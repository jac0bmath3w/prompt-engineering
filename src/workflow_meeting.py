# src/workflow_meeting.py
import os
import json
from typing import List

from llm_client import get_client, get_default_model  # used when provider != gemini
from models import ExtractedMeeting, PackagedOutput, ValidationError
from prompts import EXTRACTION_PROMPT, CLARIFICATION_PROMPT, SUMMARY_PROMPT


# ---- provider-aware chat helper
def chat(model: str, prompt: str, temperature: float = 0.2) -> str:
    provider = os.getenv("PROVIDER", "openrouter").lower()

    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        gmodel_name = os.getenv("GEMINI_MODEL", model or "gemini-1.5-flash")
        gmodel = genai.GenerativeModel(gmodel_name)
        resp = gmodel.generate_content(
            prompt,
            generation_config={"temperature": temperature}
        )
        # google-generativeai returns text directly
        return (resp.text or "").strip()

    # default: OpenRouter/OpenAI-compatible path
    client = get_client()
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


# ---- extraction with gentle retry and JSON salvage
def extract_meeting_json(transcript: str, model: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(meeting_transcript=transcript)
    for attempt in range(2):
        text = chat(model, prompt, temperature=0.2)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                chunk = text[start:end+1]
                try:
                    return json.loads(chunk)
                except Exception:
                    pass
            # tighten and retry
            prompt = prompt + "\n\nIMPORTANT: Return VALID JSON ONLY. No prose, no code fences."
    raise ValueError("Failed to parse extraction JSON after retries.")


# def find_missing_fields(d: dict) -> List[str]:
#     missing = []
#     for key in ["date", "attendees", "decisions", "action_items"]:
#         if key not in d:
#             missing.append(key)

#     if d.get("date") in (None, "null", ""):
#         missing.append("date")

#     if d.get("attendees") == []:
#         missing.append("attendees")

#     if isinstance(d.get("action_items"), list) and len(d["action_items"]) > 0:
#         if all(ai.get("deadline") in (None, "null") for ai in d["action_items"]):
#             missing.append("deadlines")
#         if any(not ai.get("task") for ai in d["action_items"]):
#             missing.append("task")
#     return sorted(set(missing))

def slugify_owner(name: str) -> str:
    return "_".join(name.strip().lower().split())

def build_missing_keys(extracted: dict) -> dict:
    """
    Inspect extracted data and return:
      - missing_fields: ["date", "attendees", "deadlines", ...] (human-ish labels)
      - owners_missing_deadlines: ["carol", "dave", ...] (slugs)
    """
    missing = []
    owners_missing = []

    # required keys check
    for key in ["date", "attendees", "decisions", "action_items"]:
        if key not in extracted:
            missing.append(key)

    if extracted.get("date") in (None, "null", ""):
        missing.append("date")
    if extracted.get("attendees") == []:
        missing.append("attendees")

    ais = extracted.get("action_items") or []
    if isinstance(ais, list) and len(ais) > 0:
        for ai in ais:
            owner = ai.get("owner") or ""
            if ai.get("deadline") in (None, "null", "") and owner:
                owners_missing.append(slugify_owner(owner))
        if owners_missing:
            missing.append("deadlines")

    return {
        "missing_fields": sorted(set(missing)),
        "owners_missing_deadlines": sorted(set(owners_missing)),
    }



def ask_clarifications(extracted: dict, model: str) -> list[dict]:
    info = build_missing_keys(extracted)
    missing_fields = info["missing_fields"]
    owners = info["owners_missing_deadlines"]

    if not missing_fields:
        return []

    # Build a concrete instruction: we want per-owner deadline questions
    prompt = CLARIFICATION_PROMPT.format(
        missing_fields=", ".join(
            [*missing_fields, *(f"deadline_for_{o}" for o in owners)]
        )
    )
    text = chat(model, prompt, temperature=0.2)
    try:
        clean_text = text.strip()
    
        # Safely remove the start fence (```json\n)
        if clean_text.startswith('```json'):
            clean_text = clean_text.removeprefix('```json').strip() 
        
        # Safely remove the end fence (\n```)
        if clean_text.endswith('```'):
            clean_text = clean_text.removesuffix('```').strip()

            # Parse JSON array of {key, question}

        obj = json.loads(clean_text)
        # keep only well-formed items
        return [
            {"key": it.get("key"), "question": it.get("question")}
            for it in obj
            if isinstance(it, dict) and it.get("key") and it.get("question")
        ][:5]  # cap to reasonable number
    # except Exception:
    #     return []
    except json.JSONDecodeError as e:
        print(f"Failed to load after cleaning: {e}")
# def ask_clarifications(missing_fields: List[str], model: str) -> List[str]:
#     if not missing_fields:
#         return []
#     prompt = CLARIFICATION_PROMPT.format(missing_fields=", ".join(missing_fields))
#     text = chat(model, prompt, temperature=0.2)
#     lines = [ln.strip("- ").strip() for ln in text.splitlines() if ln.strip()]
#     qs = [ln for ln in lines if ln.endswith("?")]
#     return qs[:3]


# def apply_clarifications(extracted: dict, user_answers: dict) -> dict:
#     patched = dict(extracted)
#     if "date" in user_answers and user_answers["date"]:
#         patched["date"] = user_answers["date"]
#     return patched

# def apply_clarifications(extracted: dict, user_answers: dict) -> dict:
#     patched = dict(extracted)
#     # meeting date
#     if user_answers.get("date"):
#         patched["date"] = user_answers["date"]

#     # per-owner deadlines: keys like "deadline_for_carol", "deadline_for_dave"
#     if isinstance(patched.get("action_items"), list):
#         for ai in patched["action_items"]:
#             owner = (ai.get("owner") or "").strip().lower()
#             if owner:
#                 key = f"deadline_for_{owner}"
#                 if user_answers.get(key):
#                     ai["deadline"] = user_answers[key]
#     return patched

import re

OWNER_DEADLINE_RE = re.compile(r"\b([A-Za-z][A-Za-z ]+)\s*[:\-–>\s]+\s*(\d{4}-\d{2}-\d{2})")

def parse_owner_deadlines(answer: str) -> dict[str, str]:
    """Extract mappings: 'carol'->'2025-10-10', 'dave'->'2025-10-09' from a freeform string."""
    out = {}
    for name, date in OWNER_DEADLINE_RE.findall(answer or ""):
        slug = slugify_owner(name)
        out[f"deadline_for_{slug}"] = date
    return out

def apply_clarifications(extracted: dict, user_answers: dict) -> dict:
    patched = dict(extracted)

    # direct date
    if user_answers.get("date"):
        patched["date"] = user_answers["date"]

    # handle a single freeform field like "deadlines" (optional UX)
    if "deadlines" in user_answers and isinstance(user_answers["deadlines"], str):
        parsed = parse_owner_deadlines(user_answers["deadlines"])
        for k, v in parsed.items():
            user_answers[k] = v

    # per-owner deadlines: keys like "deadline_for_<slug>"
    ais = patched.get("action_items") or []
    for i, ai in enumerate(ais):
        owner_slug = slugify_owner(ai.get("owner") or "")
        if not owner_slug:
            continue
        key = f"deadline_for_{owner_slug}"
        if user_answers.get(key):
            ai["deadline"] = user_answers[key]

    patched["action_items"] = ais
    return patched


def make_summary(extracted: dict, model: str) -> str:
    payload = json.dumps(extracted, ensure_ascii=False)
    prompt = SUMMARY_PROMPT.format(extracted_json=payload)
    # a bit more creative for summary
    return chat(model, prompt, temperature=0.5)


def run_workflow(transcript: str, user_answers: dict | None = None, model: str | None = None, return_questions: bool = False) -> PackagedOutput:
    provider = os.getenv("PROVIDER", "openrouter").lower()
    if model is None:
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash") if provider == "gemini" else get_default_model()

    # Step A: Extraction
    raw = extract_meeting_json(transcript, model)

    # Validate against schema
    try:
        extracted = ExtractedMeeting.model_validate(raw)
    except ValidationError as e:
        raise ValueError(f"Extraction schema validation failed: {e}") from e

    # Step B: Check & (optional) clarify
    # missing = find_missing_fields(extracted.model_dump())
    missing = build_missing_keys(extracted.model_dump())
    questions = ask_clarifications(extracted.model_dump(), model) if missing else [] #missing
    if user_answers:
        patched = apply_clarifications(extracted.model_dump(), user_answers)
        extracted = ExtractedMeeting.model_validate(patched)

    # Step C: Summary
    summary = make_summary(extracted.model_dump(), model)

    # Step D: Package
    packaged = PackagedOutput(extracted=extracted, summary=summary)
    return (packaged, questions) if return_questions else packaged
