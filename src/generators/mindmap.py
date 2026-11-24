"""
mindmap.py - Mermaid mind map generator.

Prompts Gemini to produce a Mermaid mindmap diagram capturing
the key concepts and their hierarchical relationships.
"""

from src.analyzer import analyze_transcript, analyze_long_transcript

SYSTEM_PROMPT = (
    "You are an expert at creating mind maps from educational content. "
    "You output valid Mermaid mindmap syntax. Always output ONLY the "
    "Mermaid code block — no extra commentary, no markdown fences."
)

USER_PROMPT = """Analyze the following video transcript and create a Mermaid mind map.

**Rules:**
1. Use the `mindmap` diagram type.
2. The root node should be the main topic of the video.
3. Create 3-6 main branches for key concepts.
4. Each branch can have 2-4 sub-points.
5. Keep labels concise (max 5 words each).
6. Use proper Mermaid mindmap indentation (2 spaces per level).
7. Output ONLY the raw Mermaid code — no markdown fences, no explanation.
8. Do NOT use special characters like parentheses, colons, or quotes inside node labels.

**Example format:**
mindmap
  root((Main Topic))
    Branch A
      Sub-point 1
      Sub-point 2
    Branch B
      Sub-point 3
      Sub-point 4

**Transcript:**
{transcript}"""


def generate_mindmap(transcript: str, chunks: list[str] | None = None) -> str:
    """Generate a Mermaid mind map from a transcript.

    Args:
        transcript: The full transcript text (used if chunks is None).
        chunks: Optional pre-chunked transcript for long videos.

    Returns:
        Mermaid mindmap syntax string.
    """
    if chunks and len(chunks) > 1:
        raw = analyze_long_transcript(chunks, SYSTEM_PROMPT, USER_PROMPT)
    else:
        raw = analyze_transcript(transcript, SYSTEM_PROMPT, USER_PROMPT)

    # Clean up: strip markdown fences if the model added them
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```mermaid) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    return cleaned.strip()
