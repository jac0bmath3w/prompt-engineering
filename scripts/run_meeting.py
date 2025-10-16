# # run_meeting.py

# import sys, os
# import sys, os, json
# from pathlib import Path

# home_path = os.path.dirname(os.getcwd())


# print(os.path.join(home_path, "src"))
# sys.path.append(os.path.join(home_path, "src"))

# from workflow_meeting import run_workflow

# # TRANSCRIPT = """Alice: Let's finalize the Q4 marketing budget.
# # Bob: Set it at $50,000 and allocate 60% to digital ads.
# # Carol: Campaign launch deadline is November 1.
# # Dave: Action items — Bob drafts budget proposal; Carol coordinates with design.
# # """

# TRANSCRIPT = """Meeting Notes:

# Alice: Let's move forward with the product launch.  
# Bob: Sounds good. We’ll announce it soon.  
# Carol: I’ll prepare the press release.  
# Dave: I'll work with marketing on visuals.  
# """


# # if __name__ == "__main__":
# #     result = run_workflow(TRANSCRIPT)
# #     print("\n=== EXTRACTED ===")
# #     print(result.extracted.model_dump_json(indent=2, ensure_ascii=False))
# #     print("\n=== SUMMARY ===")
# #     print(result.summary)
# if __name__ == "__main__":
#     result = run_workflow(TRANSCRIPT)
#     print("\n=== EXTRACTED ===")
#     print(json.dumps(result.extracted.model_dump(), indent=2, ensure_ascii=False))
#     print("\n=== SUMMARY ===")
#     print(result.summary)


# scripts/run_meeting.py
import json
from pathlib import Path
import sys, os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

home_path = os.path.dirname(os.getcwd())
# print(os.path.join(home_path, "src"))
sys.path.append(os.path.join(home_path, "src"))

from workflow_meeting import run_workflow  # now returns (result, questions) if asked

TRANSCRIPT = """Meeting Notes:

Alice: Let's move forward with the product launch.
Bob: Sounds good. We’ll announce it soon.
Carol: I’ll prepare the press release.
Dave: I'll work with marketing on visuals.
"""

def map_answer_to_keys(question: str, answer: str) -> dict:
    """
    Minimal heuristic to map your answer to the right key(s) in user_answers.
    - If the question mentions 'date' -> {'date': answer}
    - If the question mentions 'deadline' and a known owner name -> {'deadline_for_<owner>': answer}
    """
    q = question.lower()
    ans = answer.strip()
    if not ans:
        return {}

    if "date" in q:
        return {"date": ans}

    # crude owner detection; expand as needed
    for name in ["alice", "bob", "carol", "dave"]:
        if name in q and ("deadline" in q or "due" in q):
            return {f"deadline_for_{name}": ans}

    # fallback: no mapping
    return {}

if __name__ == "__main__":
    # Pass return_questions=True to get clarifying questions
    packaged, questions = run_workflow(TRANSCRIPT, return_questions=True)

    if questions:
        print("\nClarification questions:")
        for q in questions:
            print(f"- ({q['key']}) {q['question']}")

        # Collect answers
        user_answers = {}
        print("\nPlease answer (press Enter to skip a question):")
        for q in questions:
            ans = input(f"{q['key']}: ").strip()
            if ans:
                user_answers[q["key"]] = ans
            
            # ans = input(f"- {q}\n  Answer: ").strip()
            # if ans:
            #     user_answers.update(map_answer_to_keys(q, ans))


        if user_answers:
            # Re-run with your answers applied
            packaged = run_workflow(TRANSCRIPT, user_answers=user_answers)
        else:
            print("\n(No answers provided; using initial extraction.)")

    print("\n=== EXTRACTED ===")
    print(json.dumps(packaged.extracted.model_dump(), indent=2, ensure_ascii=False))
    print("\n=== SUMMARY ===")
    print(packaged.summary)
