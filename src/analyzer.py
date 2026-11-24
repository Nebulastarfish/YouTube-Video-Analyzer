"""
analyzer.py - LLM analysis module using Google Gemini API.

Uses the modern google-genai SDK (>= 2.3.0) with the Interactions API
to analyze transcripts and generate structured outputs.
"""

import os
import sys
import time
from dotenv import load_dotenv
from google import genai


def get_app_dir() -> str:
    """Return the directory of the running .exe (when frozen) or project root."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# Load .env: first check the folder containing the executable / script
_app_dir = get_app_dir()
_env_path = os.path.join(_app_dir, ".env")
if os.path.isfile(_env_path):
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

# High-speed model with generous free-tier quota (gemini-3.8-flash has a strict 20 req/day cap on free tier)
MODEL = "gemini-3.5-flash-lite"


def _get_api_key() -> str:
    """Retrieve Gemini API key from environment."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        env_location = os.path.join(get_app_dir(), ".env")
        raise RuntimeError(
            f"GEMINI_API_KEY not found in environment.\n"
            f"Please ensure a .env file exists at:\n  {env_location}\n"
            f"with the line: GEMINI_API_KEY=your_key_here\n\n"
            f"Get an API key from: https://aistudio.google.com/apikey"
        )
    return api_key.strip().strip('"').strip("'")


def _get_client() -> genai.Client:
    """Create and return a configured Gemini client."""
    api_key = _get_api_key()
    return genai.Client(api_key=api_key)


def analyze_transcript(
    transcript: str,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> str:
    """Send a transcript to Gemini for analysis.

    Args:
        transcript: The video transcript text.
        system_prompt: System instruction for the model.
        user_prompt: User prompt with {transcript} placeholder.
        model: Gemini model identifier (default: gemini-3.8-flash).

    Returns:
        Generated text response.
    """
    model = model or MODEL
    full_prompt = user_prompt.replace("{transcript}", transcript)

    # Combine system prompt and user prompt into a single input
    combined_input = f"{system_prompt}\n\n{full_prompt}"

    client = _get_client()
    max_retries = 3
    base_delay = 2.0

    models_to_try = [model]
    if model != "gemini-3.5-flash-lite":
        models_to_try.append("gemini-3.5-flash-lite")
    if model != "gemini-3.1-flash-lite":
        models_to_try.append("gemini-3.1-flash-lite")

    last_error = None
    for current_model in models_to_try:
        for attempt in range(max_retries):
            try:
                interaction = client.interactions.create(
                    model=current_model,
                    input=combined_input,
                    store=False,  # Don't store interactions for privacy
                )
                return interaction.output_text
            except Exception as e:
                err_msg = str(e)
                last_error = e
                # Check for rate limit / 429
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Rate limit" in err_msg:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        # Try next fallback model
                        break

            if any(keyword in err_msg for keyword in [
                "ACCESS_TOKEN_TYPE_UNSUPPORTED",
                "API_KEY_SERVICE_BLOCKED",
                "invalid authentication credentials",
                "401",
                "UNAUTHENTICATED",
            ]):
                raise RuntimeError(
                    "Gemini API Authentication Failed.\n\n"
                    "Your API key may be invalid or expired.\n"
                    "How to fix:\n"
                    "1. Go to: https://aistudio.google.com/apikey\n"
                    "2. Click 'Create API key' to create a fresh key.\n"
                    "3. Update your .env file with: GEMINI_API_KEY=your_new_key\n"
                    "4. Restart the app."
                ) from e
            if attempt == max_retries - 1 and current_model == models_to_try[-1]:
                raise

    if last_error:
        raise last_error
    raise RuntimeError("Analysis failed: all model retries exhausted.")


def analyze_long_transcript(
    chunks: list[str],
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> str:
    """Analyze a multi-chunk transcript and merge results."""
    if len(chunks) == 1:
        return analyze_transcript(chunks[0], system_prompt, user_prompt, model)

    partial_results: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        chunk_user_prompt = (
            f"This is part {i} of {len(chunks)} of the video transcript.\n"
            + user_prompt
        )
        result = analyze_transcript(chunk, system_prompt, chunk_user_prompt, model)
        partial_results.append(f"--- Section {i} ---\n{result}")

    merged_input = "\n\n".join(partial_results)
    merge_prompt = (
        "Below are partial analyses from different sections of the same video. "
        "Consolidate and merge them into a single, cohesive, unified output without duplicates. "
        "Retain the exact format required:\n\n"
        f"{merged_input}"
    )
    return analyze_transcript("", system_prompt, merge_prompt, model)
