"""
transcript.py - YouTube transcript extraction module.

Uses youtube-transcript-api as the primary source. Falls back to yt-dlp
when the API is blocked (IP ban, rate limits, etc.).
"""

import os
import re
import tempfile

from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """Extract the video ID from various YouTube URL formats.

    Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID
        - Plain VIDEO_ID string

    Args:
        url: A YouTube URL or raw video ID.

    Returns:
        The 11-character video ID.

    Raises:
        ValueError: If no valid video ID can be extracted.
    """
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


# Comprehensive list of English regional codes and common fallbacks
DEFAULT_LANGUAGES = [
    "en",
    "en-US",
    "en-GB",
    "en-CA",
    "en-AU",
    "en-IN",
    "en-IE",
    "en-NZ",
    "en-ZA",
    "en-SG",
]


# ---------------------------------------------------------------------------
# yt-dlp fallback helpers
# ---------------------------------------------------------------------------

def _parse_vtt_text(content: str) -> list[dict]:
    """Parse a VTT/SRT subtitle file into a list of {text, start, duration} dicts."""
    entries: list[dict] = []
    # Match timestamps like 00:00:01.234 --> 00:00:05.678
    ts_pattern = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{3})"
    )

    def _ts_to_seconds(ts: str) -> float:
        ts = ts.replace(",", ".")
        parts = ts.split(":")
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        m = ts_pattern.search(lines[i])
        if m:
            start = _ts_to_seconds(m.group(1))
            end = _ts_to_seconds(m.group(2))
            i += 1
            text_lines: list[str] = []
            while i < len(lines) and lines[i].strip() and not ts_pattern.search(lines[i]):
                # Skip VTT positioning tags and numeric cue identifiers
                line = lines[i].strip()
                if line.isdigit():
                    i += 1
                    continue
                # Strip HTML-like tags (<c>, </c>, <00:00:01.234>, etc.)
                line = re.sub(r"<[^>]+>", "", line)
                if line:
                    text_lines.append(line)
                i += 1
            text = " ".join(text_lines)
            if text:
                entries.append({
                    "text": text,
                    "start": round(start, 3),
                    "duration": round(end - start, 3),
                })
        else:
            i += 1

    # Deduplicate (yt-dlp VTT often repeats lines in overlapping cues)
    seen: set[str] = set()
    deduped: list[dict] = []
    for e in entries:
        if e["text"] not in seen:
            seen.add(e["text"])
            deduped.append(e)
    return deduped


def _fetch_via_ytdlp(video_id: str, languages: list[str] | None = None) -> list[dict]:
    """Fetch transcript using yt-dlp as fallback. Returns list of {text, start, duration}."""
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError(
            "yt-dlp is not installed. Install it with: pip install yt-dlp"
        )

    if languages is None:
        languages = list(DEFAULT_LANGUAGES)

    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = os.path.join(tmpdir, "subs.%(ext)s")
        ydl_opts = {
            "skip_download": True,
            "writeautomaticsub": True,
            "writesubtitles": True,
            "subtitleslangs": languages,
            "subtitlesformat": "vtt",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # Find the subtitle file yt-dlp wrote
        sub_file = None
        for f in os.listdir(tmpdir):
            if f.endswith((".vtt", ".srt")):
                sub_file = os.path.join(tmpdir, f)
                break

        if not sub_file:
            # Check if subtitles were embedded in info dict
            raise RuntimeError(
                f"yt-dlp could not find subtitles for video {video_id}. "
                "The video may not have captions available."
            )

        with open(sub_file, "r", encoding="utf-8") as fh:
            content = fh.read()

    entries = _parse_vtt_text(content)
    if not entries:
        raise RuntimeError(f"yt-dlp downloaded subtitles but they were empty for video {video_id}")
    return entries


# ---------------------------------------------------------------------------
# Core transcript retrieval
# ---------------------------------------------------------------------------

def _get_raw_transcript_data(video_id: str, languages: list[str] | None = None) -> list:
    """Retrieve raw transcript entries using multi-language detection and auto-translation fallback.

    1. Tries direct fetch with requested or broad English regional variants.
    2. Falls back to transcript listing to find manual or auto-generated matching transcripts.
    3. If no direct match is found, auto-translates any translatable transcript to English.
    4. If translation is unavailable, falls back to the original available language.
    5. If all youtube-transcript-api methods fail, uses yt-dlp as final fallback.
    """
    if languages is None:
        languages = list(DEFAULT_LANGUAGES)

    ytt_api = YouTubeTranscriptApi()

    # Attempt 1: Direct fetch with the broad language list
    try:
        try:
            return list(YouTubeTranscriptApi.get_transcript(video_id, languages=languages))
        except (AttributeError, TypeError):
            return list(ytt_api.fetch(video_id, languages=languages))
    except Exception as e_direct:
        # Attempt 2: Use transcript listing to find matching, auto-generated, or translatable transcripts
        try:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            except (AttributeError, TypeError):
                transcript_list = ytt_api.list(video_id)

            found = None

            # 2a: Try manually created or generated in our languages
            try:
                found = transcript_list.find_transcript(languages)
            except Exception:
                pass

            if not found:
                try:
                    found = transcript_list.find_generated_transcript(languages)
                except Exception:
                    pass

            # 2b: Try translating any available transcript to English
            if not found:
                for t in transcript_list:
                    if getattr(t, "is_translatable", False):
                        try:
                            found = t.translate("en")
                            break
                        except Exception:
                            pass

            # 2c: Fallback to the first available transcript in whatever language
            if not found:
                for t in transcript_list:
                    found = t
                    break

            if found:
                return list(found.fetch())
            raise e_direct
        except Exception:
            pass  # Fall through to yt-dlp fallback

    # Attempt 3: yt-dlp fallback (works even when youtube-transcript-api is IP-blocked)
    try:
        return _fetch_via_ytdlp(video_id, languages=languages)
    except Exception as e_ytdlp:
        raise RuntimeError(
            f"All transcript sources failed for video {video_id}.\n"
            f"youtube-transcript-api: {e_direct}\n"
            f"yt-dlp fallback: {e_ytdlp}"
        )


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str:
    """Fetch the full transcript text for a YouTube video.

    Args:
        video_id: The YouTube video ID.
        languages: Preferred language codes (e.g., ["en", "en-US", "hi"]).
                   Defaults to comprehensive English variants.

    Returns:
        The full transcript as a single string.

    Raises:
        Exception: If no transcript is available.
    """
    transcript_data = _get_raw_transcript_data(video_id, languages=languages)

    texts = []
    for entry in transcript_data:
        if isinstance(entry, dict):
            texts.append(entry.get("text", ""))
        else:
            texts.append(getattr(entry, "text", str(entry)))

    full_text = " ".join(texts)
    if not full_text.strip():
        raise ValueError(f"Transcript is empty for video: {video_id}")
    return full_text


def fetch_transcript_with_timestamps(
    video_id: str, languages: list[str] | None = None
) -> list[dict]:
    """Fetch the transcript with timestamps for each segment.

    Args:
        video_id: The YouTube video ID.
        languages: Preferred language codes. Defaults to comprehensive English variants.

    Returns:
        A list of dicts with 'text', 'start', and 'duration' keys.
    """
    transcript_data = _get_raw_transcript_data(video_id, languages=languages)

    results = []
    for entry in transcript_data:
        if isinstance(entry, dict):
            results.append({
                "text": entry.get("text", ""),
                "start": entry.get("start", 0),
                "duration": entry.get("duration", 0),
            })
        else:
            results.append({
                "text": getattr(entry, "text", ""),
                "start": getattr(entry, "start", 0),
                "duration": getattr(entry, "duration", 0),
            })
    return results


def chunk_transcript(text: str, max_chunk_size: int = 3000) -> list[str]:
    """Split a transcript into smaller chunks for LLM processing.

    Splits on sentence boundaries to avoid cutting mid-sentence.

    Args:
        text: The full transcript text.
        max_chunk_size: Maximum characters per chunk.

    Returns:
        A list of text chunks.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        if current_length + len(sentence) > max_chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
        current_chunk.append(sentence)
        current_length += len(sentence) + 1

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
