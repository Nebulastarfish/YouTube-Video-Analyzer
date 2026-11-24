"""
utils.py - Utility functions for the YouTube Video Analyzer.
Handles saving files relative to the executable directory when frozen,
formats Markdown documents optimized for Obsidian and other PKM apps,
and names folders and files using the actual YouTube video title.
"""

import os
import sys
import re
import json
import urllib.request
import shutil
from datetime import datetime


def get_app_dir() -> str:
    """Return the directory of the running .exe (when frozen) or project root."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def sanitize_filename(name: str) -> str:
    """Convert a string into a safe filesystem filename or directory name."""
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    safe = re.sub(r"\s+", " ", safe.strip())
    # Keep up to 75 chars to avoid long Windows path limits
    return safe[:75].strip()


def save_output(content: str, filename: str, output_dir: str = "output") -> str:
    """Save content to a file in the output directory."""
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(get_app_dir(), output_dir)

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def create_markdown_report(
    video_id: str,
    steps: str = "",
    mindmap: str = "",
    flowchart: str = "",
    transcript: str = "",
    title: str = "",
) -> str:
    """Combine selected outputs into a single Obsidian-ready Markdown report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    iso_date = datetime.now().strftime("%Y-%m-%d")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    display_title = title.strip() or f"YouTube Video Analysis - {video_id}"

    # Build list of related links and table of contents for generated sections
    related = []
    toc = []
    if steps:
        related.append("[[steps]]")
        toc.append("- [[#📋 Step-by-Step Procedure]]")
    if mindmap:
        related.append("[[mindmap]]")
        toc.append("- [[#🧠 Mind Map]]")
    if flowchart:
        related.append("[[flowchart]]")
        toc.append("- [[#📊 Flowchart]]")
    if transcript:
        related.append("[[transcript]]")
        toc.append("- [[#📝 Raw Transcript]]")

    related_str = " • ".join(related)

    sections = [
        f"""---
title: "{display_title}"
source: "{video_url}"
date: {iso_date}
tags:
  - youtube-summary
  - obsidian
---

# 🎬 {display_title}

> **Video:** [{video_url}]({video_url})  
> **Generated:** {timestamp}  """
    ]

    if related_str:
        sections.append(f"> **Related Notes:** {related_str}\n\n---\n")
    else:
        sections.append("\n---\n")

    if toc:
        sections.append(f"## 📑 Contents\n" + "\n".join(toc) + "\n\n---\n")

    if steps:
        sections.append(f"{steps}\n\n---\n")

    if mindmap:
        sections.append(f"## 🧠 Mind Map\n\n```mermaid\n{mindmap}\n```\n\n---\n")

    if flowchart:
        sections.append(f"## 📊 Flowchart\n\n```mermaid\n{flowchart}\n```\n\n---\n")

    if transcript:
        sections.append(f"""## 📝 Raw Transcript

<details>
<summary>Click to view full transcript ({len(transcript)} characters)</summary>

{transcript}

</details>
""")

    return "\n".join(sections)


def create_obsidian_steps(video_id: str, steps: str, title: str = "") -> str:
    """Format the step-by-step procedure as an Obsidian note."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    display_title = title.strip() or f"Steps - {video_id}"
    return f"""---
title: "{display_title}"
source: "{video_url}"
tags:
  - procedure
  - steps
  - guide
---

# 📋 Step-by-Step Procedure

> **Source Video:** [{video_url}]({video_url})  
> **Main Report:** [[report]] • **Mind Map:** [[mindmap]] • **Flowchart:** [[flowchart]]

---

{steps}
"""


def create_obsidian_mindmap(video_id: str, mindmap: str, title: str = "") -> str:
    """Format the mind map as an Obsidian note with native Mermaid diagram."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    display_title = title.strip() or f"Mind Map - {video_id}"
    return f"""---
title: "{display_title}"
source: "{video_url}"
tags:
  - mindmap
  - mermaid
---

# 🧠 Mind Map

> **Source Video:** [{video_url}]({video_url})  
> **Main Report:** [[report]] • **Steps:** [[steps]] • **Flowchart:** [[flowchart]]

```mermaid
{mindmap}
```
"""


def create_obsidian_flowchart(video_id: str, flowchart: str, title: str = "") -> str:
    """Format the flowchart as an Obsidian note with native Mermaid diagram."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    display_title = title.strip() or f"Flowchart - {video_id}"
    return f"""---
title: "{display_title}"
source: "{video_url}"
tags:
  - flowchart
  - mermaid
  - process
---

# 📊 Flowchart

> **Source Video:** [{video_url}]({video_url})  
> **Main Report:** [[report]] • **Steps:** [[steps]] • **Mind Map:** [[mindmap]]

```mermaid
{flowchart}
```
"""


def create_obsidian_transcript(video_id: str, transcript: str, title: str = "") -> str:
    """Format the raw transcript as an Obsidian note."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    display_title = title.strip() or f"Transcript - {video_id}"
    return f"""---
title: "{display_title}"
source: "{video_url}"
tags:
  - transcript
  - raw-notes
---

# 📝 Raw Transcript

> **Source Video:** [{video_url}]({video_url})  
> **Main Report:** [[report]]

---

{transcript}
"""


def fetch_video_metadata(video_id: str) -> dict:
    """Fetch video title, author, and thumbnail from YouTube oEmbed."""
    title = f"Video {video_id}"
    author = "YouTube"
    thumbnail = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            title = data.get("title") or title
            author = data.get("author_name") or author
            thumbnail = data.get("thumbnail_url") or thumbnail
    except Exception:
        pass

    return {
        "video_id": video_id,
        "title": title,
        "author": author,
        "thumbnail": thumbnail,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def find_video_output_dir(video_id: str) -> str | None:
    """Find the directory for a video_id, preferring title-based folders and most recent."""
    output_dir = os.path.join(get_app_dir(), "output")
    if not os.path.isdir(output_dir):
        return None

    candidates = []
    for entry in os.listdir(output_dir):
        entry_path = os.path.join(output_dir, entry)
        if not os.path.isdir(entry_path) or entry.startswith("."):
            continue

        is_titled = f"[{video_id}]" in entry or entry.endswith(f"_{video_id}")
        is_match = False
        if is_titled or entry == video_id:
            is_match = True
        else:
            meta_file = os.path.join(entry_path, "meta.json")
            if os.path.isfile(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        if meta.get("video_id") == video_id:
                            is_match = True
                except Exception:
                    pass

        if is_match:
            try:
                mtime = os.path.getmtime(entry_path)
            except Exception:
                mtime = 0
            candidates.append((1 if is_titled else 0, mtime, entry_path))

    if candidates:
        candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
        return candidates[0][2]

    # Direct fallback
    direct = os.path.join(output_dir, video_id)
    if os.path.isdir(direct):
        return direct
    return None


def save_all_analysis_documents(
    video_id: str,
    steps: str = "",
    mindmap: str = "",
    flowchart: str = "",
    transcript: str = "",
    output_base_dir: str = "output",
    title: str = "",
) -> dict:
    """Save all analysis outputs into a folder named with the video title and ID.

    Generates both title-based filenames (e.g. 'How to Code - Steps.md')
    and canonical aliases ('steps.md') for maximum Obsidian compatibility.
    """
    if not title:
        meta = fetch_video_metadata(video_id)
        title = meta.get("title", f"Video {video_id}")
    else:
        meta = fetch_video_metadata(video_id)
        meta["title"] = title

    safe_title = sanitize_filename(title)
    if not safe_title:
        safe_title = video_id

    # Create folder named with video title and video_id: e.g. "7 Boring Businesses [qZJgIdi02qQ]"
    folder_name = f"{safe_title} [{video_id}]"
    target_dir = os.path.join(output_base_dir, folder_name)

    if not os.path.isabs(target_dir):
        abs_target_dir = os.path.join(get_app_dir(), target_dir)
    else:
        abs_target_dir = target_dir

    os.makedirs(abs_target_dir, exist_ok=True)
    saved_files = []

    # 1. Master Report (.md) - Save with video title and canonical name
    report_content = create_markdown_report(
        video_id, steps=steps, mindmap=mindmap, flowchart=flowchart, transcript=transcript, title=title
    )
    saved_files.append(save_output(report_content, f"{safe_title} - Report.md", abs_target_dir))
    saved_files.append(save_output(report_content, "report.md", abs_target_dir))

    # 2. Steps (.md) - only if steps were generated
    if steps:
        steps_doc = create_obsidian_steps(video_id, steps, title=title)
        saved_files.append(save_output(steps_doc, f"{safe_title} - Steps.md", abs_target_dir))
        saved_files.append(save_output(steps_doc, "steps.md", abs_target_dir))

    # 3. Mind Map (.md and .mmd) - only if mindmap was generated
    if mindmap:
        mindmap_doc = create_obsidian_mindmap(video_id, mindmap, title=title)
        saved_files.append(save_output(mindmap_doc, f"{safe_title} - Mind Map.md", abs_target_dir))
        saved_files.append(save_output(mindmap_doc, "mindmap.md", abs_target_dir))
        saved_files.append(save_output(mindmap, f"{safe_title} - Mind Map.mmd", abs_target_dir))
        saved_files.append(save_output(mindmap, "mindmap.mmd", abs_target_dir))

    # 4. Flowchart (.md and .mmd) - only if flowchart was generated
    if flowchart:
        flowchart_doc = create_obsidian_flowchart(video_id, flowchart, title=title)
        saved_files.append(save_output(flowchart_doc, f"{safe_title} - Flowchart.md", abs_target_dir))
        saved_files.append(save_output(flowchart_doc, "flowchart.md", abs_target_dir))
        saved_files.append(save_output(flowchart, f"{safe_title} - Flowchart.mmd", abs_target_dir))
        saved_files.append(save_output(flowchart, "flowchart.mmd", abs_target_dir))

    # 5. Transcript (.md) - only if transcript was included
    if transcript:
        transcript_doc = create_obsidian_transcript(video_id, transcript, title=title)
        saved_files.append(save_output(transcript_doc, f"{safe_title} - Transcript.md", abs_target_dir))
        saved_files.append(save_output(transcript_doc, "transcript.md", abs_target_dir))

    # 6. Save metadata (meta.json) for fast history rendering
    meta["video_id"] = video_id
    meta["folder_name"] = folder_name
    meta["safe_title"] = safe_title
    meta["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta["has_steps"] = bool(steps)
    meta["has_mindmap"] = bool(mindmap)
    meta["has_flowchart"] = bool(flowchart)
    meta["has_transcript"] = bool(transcript)

    meta_path = os.path.join(abs_target_dir, "meta.json")
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        saved_files.append(meta_path)
    except Exception:
        pass

    return {
        "output_dir": abs_target_dir,
        "saved_files": saved_files,
        "metadata": meta,
        "folder_name": folder_name,
    }


def get_history_list() -> list[dict]:
    """Retrieve list of all analyzed videos sorted by timestamp descending."""
    output_dir = os.path.join(get_app_dir(), "output")
    if not os.path.isdir(output_dir):
        return []

    items = []
    seen_ids = set()

    for entry in os.listdir(output_dir):
        entry_path = os.path.join(output_dir, entry)
        if not os.path.isdir(entry_path) or entry.startswith("."):
            continue

        # Look for report.md or any *Report.md
        has_report = any(f.endswith("report.md") or f.endswith("Report.md") for f in os.listdir(entry_path))
        if not has_report:
            continue

        meta_file = os.path.join(entry_path, "meta.json")
        meta = {}
        if os.path.isfile(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                pass

        # Deduce video_id
        video_id = meta.get("video_id")
        if not video_id:
            # Check for [video_id] bracket pattern
            m = re.search(r"\[([a-zA-Z0-9_-]{11})\]", entry)
            if m:
                video_id = m.group(1)
            elif len(entry) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", entry):
                video_id = entry
            else:
                video_id = entry

        if video_id in seen_ids:
            continue
        seen_ids.add(video_id)

        if not meta or not meta.get("title"):
            meta = fetch_video_metadata(video_id)
            meta["folder_name"] = entry
            mtime = os.path.getmtime(entry_path)
            meta["timestamp"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        items.append({
            "video_id": video_id,
            "title": meta.get("title", f"Video {video_id}"),
            "author": meta.get("author", "YouTube"),
            "thumbnail": meta.get("thumbnail", f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"),
            "timestamp": meta.get("timestamp", ""),
            "folder_name": entry,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "has_steps": meta.get("has_steps", True),
            "has_mindmap": meta.get("has_mindmap", True),
            "has_flowchart": meta.get("has_flowchart", True),
        })

    # Sort newest first
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return items


def get_history_item(video_id: str) -> dict | None:
    """Load full analysis outputs for a previously analyzed video."""
    target_dir = find_video_output_dir(video_id)
    if not target_dir or not os.path.isdir(target_dir):
        return None

    def read_file(name: str) -> str:
        # Try exact filename first, then check pattern (e.g. * - Steps.md)
        path = os.path.join(target_dir, name)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        # Check for matching suffix
        for f in os.listdir(target_dir):
            if f.lower().endswith(name.lower()):
                with open(os.path.join(target_dir, f), "r", encoding="utf-8") as file_handle:
                    return file_handle.read()
        return ""

    meta = {}
    meta_path = os.path.join(target_dir, "meta.json")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass
    if not meta:
        meta = fetch_video_metadata(video_id)

    # Mindmap: prefer raw mmd, or extract from mindmap.md
    mindmap = read_file("mindmap.mmd")
    if not mindmap:
        mindmap_md = read_file("mindmap.md")
        m = re.search(r"```mermaid\s*\n(.*?)\n```", mindmap_md, re.DOTALL)
        mindmap = m.group(1).strip() if m else mindmap_md

    # Flowchart: prefer raw mmd
    flowchart = read_file("flowchart.mmd")
    if not flowchart:
        flowchart_md = read_file("flowchart.md")
        m = re.search(r"```mermaid\s*\n(.*?)\n```", flowchart_md, re.DOTALL)
        flowchart = m.group(1).strip() if m else flowchart_md

    steps = read_file("steps.md")
    report = read_file("report.md")

    return {
        "video_id": video_id,
        "title": meta.get("title", f"Video {video_id}"),
        "author": meta.get("author", "YouTube"),
        "thumbnail": meta.get("thumbnail", f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"),
        "timestamp": meta.get("timestamp", ""),
        "has_steps": bool(steps),
        "has_mindmap": bool(mindmap),
        "has_flowchart": bool(flowchart),
        "steps": steps,
        "mindmap": mindmap,
        "flowchart": flowchart,
        "report": report,
        "output_dir": target_dir,
    }


def delete_history_item(video_id: str) -> bool:
    """Delete an analysis directory from the output folder."""
    target_dir = find_video_output_dir(video_id)
    if target_dir and os.path.isdir(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)
        return True
    return False
