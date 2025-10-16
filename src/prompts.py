# src/prompts.py

EXTRACTION_PROMPT = """You are an executive assistant.
From the transcript, extract structured meeting data.

Return VALID JSON ONLY with keys exactly:
- date (YYYY-MM-DD or null)
- attendees (array of strings)
- decisions (array of strings)
- action_items (array of objects with keys: owner, task, deadline [YYYY-MM-DD or null])

Rules:
- Do not invent facts. If unknown, use null or [].
- No text outside the JSON.

Transcript:
{meeting_transcript}
"""

# CLARIFICATION_PROMPT = """You are a helpful assistant.
# The following fields were missing or null: {missing_fields}.
# Ask at most 3 concise questions to fill ONLY those fields.
# Return a numbered list of questions (no other text)."""

CLARIFICATION_PROMPT = """You are a helpful assistant. We extracted meeting data but these fields are missing:
{missing_fields}

Return a VALID JSON array of clarification questions where each item has:
- key: a machine-readable key (e.g., "date" or "deadline_for_<owner_slug>")
- question: a concise user-facing question

Rules:
- For missing meeting date, include one item with key "date".
- For missing deadlines, include one item per owner with key "deadline_for_<owner_slug>" where owner_slug is the lowercase owner name with spaces replaced by underscores (e.g., "deadline_for_alice_smith").
- Only include keys for fields that are missing.
- No text outside the JSON.
"""


SUMMARY_PROMPT = """You are a professional summarizer.
Using ONLY this JSON, write a 3–5 sentence summary highlighting decisions and action items.
Keep it factual; do not invent.

JSON:
{extracted_json}
"""
