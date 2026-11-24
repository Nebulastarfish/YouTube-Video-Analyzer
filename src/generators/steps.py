"""
steps.py - Step-by-step procedure generator.

Prompts Gemini to extract an actionable, numbered procedure from a transcript.
"""

from src.analyzer import analyze_transcript, analyze_long_transcript

SYSTEM_PROMPT = (
    "You are an expert video analyst and technical writer. "
    "Your job is to extract clear, actionable step-by-step procedures "
    "from video transcripts. Be precise and include prerequisites, "
    "warnings, and tips where relevant."
)

USER_PROMPT = """Analyze the following video transcript and extract a detailed step-by-step procedure.

**Format your response exactly like this:**

## 📋 Step-by-Step Procedure

### Prerequisites
- List any prerequisites, tools, or knowledge needed

### Steps

1. **Step Name** — Clear description of what to do.
   - Sub-details or tips if needed
   
2. **Step Name** — Clear description of what to do.

(Continue for all steps...)

### ⚠️ Warnings & Tips
- Any important warnings or pro tips mentioned

---

**Transcript:**
{transcript}"""


def generate_steps(transcript: str, chunks: list[str] | None = None) -> str:
    """Generate a step-by-step procedure from a transcript.

    Args:
        transcript: The full transcript text (used if chunks is None).
        chunks: Optional pre-chunked transcript for long videos.

    Returns:
        Formatted markdown string with the step-by-step procedure.
    """
    if chunks and len(chunks) > 1:
        return analyze_long_transcript(chunks, SYSTEM_PROMPT, USER_PROMPT)
    return analyze_transcript(transcript, SYSTEM_PROMPT, USER_PROMPT)
