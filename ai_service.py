import os
import json
import re

from google import genai

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_VALID_DIFFICULTIES = {"Beginner", "Intermediate", "Advanced"}

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file before submitting issues."
        )
    return genai.Client(api_key=api_key)


def _build_prompt(language: str, issue_description: str) -> str:
    return f"""You are a senior software engineering mentor reviewing a code problem
reported by a student. Analyze the issue below and respond with your assessment.

Respond with ONLY a single valid JSON object — no markdown code fences, no
preamble, no trailing commentary. Use exactly this schema:

{{
  "category": "<a short, specific error/topic category, e.g. 'Null Reference Error', 'Off-by-one Loop Bug', 'Async/Await Misuse'>",
  "difficulty": "<exactly one of: Beginner, Intermediate, Advanced>",
  "recommendation": "<2-4 sentences of concrete, actionable guidance and the specific concept(s) or docs the student should study next>"
}}

Programming language: {language}

Issue description:
\"\"\"
{issue_description}
\"\"\"
"""


def _extract_json(raw_text: str) -> dict:
    cleaned = _FENCE_RE.sub("", raw_text.strip()).strip()
    return json.loads(cleaned)


def analyze_issue(language: str, issue_description: str) -> dict:
    """
    Runs the full AI evaluation pipeline for one submitted issue.

    Returns:
        {"category": str, "difficulty": str, "recommendation": str}

    Raises:
        RuntimeError / json.JSONDecodeError / Exception on any upstream failure
        (network, auth, quota, malformed output, etc). Intentionally NOT
        swallowed here — the route controller owns fault-tolerance handling.
    """
    client = _get_client()
    prompt = _build_prompt(language, issue_description)

    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("AI model returned an empty response.")

    data = _extract_json(raw_text)

    category = str(data.get("category", "")).strip() or "Uncategorized"
    difficulty = str(data.get("difficulty", "")).strip()
    if difficulty not in _VALID_DIFFICULTIES:
        difficulty = "Intermediate"
    recommendation = str(data.get("recommendation", "")).strip() or "No recommendation generated."

    return {
        "category": category,
        "difficulty": difficulty,
        "recommendation": recommendation,
    }
