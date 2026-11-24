"""
flowchart.py - Mermaid flowchart generator.

Prompts Gemini to produce a Mermaid flowchart diagram showing
the process or workflow described in the video.
"""

from src.analyzer import analyze_transcript, analyze_long_transcript

SYSTEM_PROMPT = (
    "You are an expert at creating process flowcharts from educational content. "
    "You output valid Mermaid flowchart syntax. Always output ONLY the "
    "Mermaid code block — no extra commentary, no markdown fences."
)

USER_PROMPT = """Analyze the following video transcript and create a Mermaid flowchart.

**Rules:**
1. Use `flowchart TD` (top-down) direction.
2. Show the main process or workflow described in the video.
3. Use decision diamonds {{}} for any conditional/branching points.
4. Use rectangles [] for action steps.
5. Use rounded rectangles () for start/end nodes.
6. Keep labels concise (max 6 words each).
7. Use unique node IDs (A, B, C... or descriptive like START, STEP1).
8. Output ONLY the raw Mermaid code — no markdown fences, no explanation.
9. Do NOT use special characters that would break Mermaid syntax.
10. Use --> for connections, with optional labels like -->|Yes| or -->|No|.

**Example format:**
flowchart TD
    START([Start]) --> A[First Step]
    A --> B{{Decision Point?}}
    B -->|Yes| C[Do This]
    B -->|No| D[Do That]
    C --> END([End])
    D --> END

**Transcript:**
{transcript}"""


def generate_flowchart(transcript: str, chunks: list[str] | None = None) -> str:
    """Generate a Mermaid flowchart from a transcript.

    Args:
        transcript: The full transcript text (used if chunks is None).
        chunks: Optional pre-chunked transcript for long videos.

    Returns:
        Mermaid flowchart syntax string.
    """
    if chunks and len(chunks) > 1:
        raw = analyze_long_transcript(chunks, SYSTEM_PROMPT, USER_PROMPT)
    else:
        raw = analyze_transcript(transcript, SYSTEM_PROMPT, USER_PROMPT)

    # Clean up: strip markdown fences if the model added them
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    return cleaned.strip()
