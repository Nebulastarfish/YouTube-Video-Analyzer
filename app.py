"""
app.py - Flask web server for the YouTube Video Analyzer.

Serves the web interface and provides an SSE-based API endpoint
that streams progress updates as each analysis stage completes.
Supports running standalone or as the backend for a PyWebView desktop app.
"""

import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import json
import queue
import threading

from flask import Flask, render_template, request, Response, jsonify

# Fix PyInstaller bundle path for templates
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    template_folder = os.path.join(sys._MEIPASS, "templates")
    app = Flask(__name__, template_folder=template_folder)
else:
    app = Flask(__name__, template_folder="templates")

from src.transcript import extract_video_id, fetch_transcript, chunk_transcript
from src.generators import generate_steps, generate_mindmap, generate_flowchart
from src.utils import (
    create_markdown_report,
    save_all_analysis_documents,
    get_app_dir,
    get_history_list,
    get_history_item,
    delete_history_item,
    fetch_video_metadata,
)


@app.route("/")
def index():
    """Serve the main web interface."""
    return render_template("index.html")


@app.route("/api/analyze/stream")
def analyze_stream():
    """SSE endpoint that streams progress updates during analysis.

    Query params:
        video: YouTube URL or video ID
        gen_steps: "true" or "false" (default: "true")
        gen_mindmap: "true" or "false" (default: "true")
        gen_flowchart: "true" or "false" (default: "true")
        include_transcript: "true" or "false" (default: "true")
    """
    video = request.args.get("video", "").strip()
    gen_steps = request.args.get("gen_steps", "true").lower() == "true"
    gen_mindmap = request.args.get("gen_mindmap", "true").lower() == "true"
    gen_flowchart = request.args.get("gen_flowchart", "true").lower() == "true"
    include_transcript = request.args.get("include_transcript", "true").lower() == "true"

    if not video:
        def error_stream():
            yield _sse_event({"step": "error", "message": "No video URL provided."})
        return Response(error_stream(), mimetype="text/event-stream")

    event_queue: queue.Queue = queue.Queue()

    def worker():
        """Run the selective analysis pipeline, pushing events to the queue."""
        try:
            # Step 1: Extract video ID and fetch metadata early
            video_id = extract_video_id(video)
            meta = fetch_video_metadata(video_id)
            video_title = meta.get("title", f"Video {video_id}")

            event_queue.put({
                "step": "info",
                "message": f"Analyzing: {video_title}",
                "title": video_title,
                "video_id": video_id,
                "thumbnail": meta.get("thumbnail"),
            })

            # Step 2: Fetch transcript
            event_queue.put({
                "step": "transcript",
                "message": f"Fetching transcript for {video_id}...",
                "status": "running",
            })
            transcript = fetch_transcript(video_id)
            chunks = chunk_transcript(transcript)
            event_queue.put({
                "step": "transcript",
                "message": f"Transcript fetched — {len(transcript)} chars, {len(chunks)} chunk(s)",
                "status": "done",
            })

            # Step 3: Generate steps (if selected)
            steps_output = ""
            if gen_steps:
                event_queue.put({
                    "step": "steps",
                    "message": "Generating step-by-step procedure...",
                    "status": "running",
                })
                steps_output = generate_steps(transcript, chunks)
                event_queue.put({
                    "step": "steps",
                    "message": "Step-by-step procedure ready",
                    "status": "done",
                    "data": steps_output,
                })
            else:
                event_queue.put({
                    "step": "steps",
                    "message": "Step-by-step procedure skipped",
                    "status": "skipped",
                })

            # Step 4: Generate mind map (if selected)
            mindmap_output = ""
            if gen_mindmap:
                event_queue.put({
                    "step": "mindmap",
                    "message": "Generating mind map...",
                    "status": "running",
                })
                mindmap_output = generate_mindmap(transcript, chunks)
                event_queue.put({
                    "step": "mindmap",
                    "message": "Mind map ready",
                    "status": "done",
                    "data": mindmap_output,
                })
            else:
                event_queue.put({
                    "step": "mindmap",
                    "message": "Mind map skipped",
                    "status": "skipped",
                })

            # Step 5: Generate flowchart (if selected)
            flowchart_output = ""
            if gen_flowchart:
                event_queue.put({
                    "step": "flowchart",
                    "message": "Generating flowchart...",
                    "status": "running",
                })
                flowchart_output = generate_flowchart(transcript, chunks)
                event_queue.put({
                    "step": "flowchart",
                    "message": "Flowchart ready",
                    "status": "done",
                    "data": flowchart_output,
                })
            else:
                event_queue.put({
                    "step": "flowchart",
                    "message": "Flowchart skipped",
                    "status": "skipped",
                })

            # Step 6: Build report and save all Obsidian documents with title
            transcript_text = transcript if include_transcript else ""
            save_info = save_all_analysis_documents(
                video_id=video_id,
                steps=steps_output,
                mindmap=mindmap_output,
                flowchart=flowchart_output,
                transcript=transcript_text,
                title=video_title,
            )
            report = create_markdown_report(
                video_id=video_id,
                steps=steps_output,
                mindmap=mindmap_output,
                flowchart=flowchart_output,
                transcript=transcript_text,
                title=video_title,
            )

            event_queue.put({
                "step": "complete",
                "message": "Analysis complete!",
                "data": json.dumps({
                    "steps": steps_output,
                    "mindmap": mindmap_output,
                    "flowchart": flowchart_output,
                    "report": report,
                    "video_id": video_id,
                    "title": video_title,
                    "has_steps": bool(steps_output),
                    "has_mindmap": bool(mindmap_output),
                    "has_flowchart": bool(flowchart_output),
                    "has_transcript": bool(transcript_text),
                    "output_dir": save_info["output_dir"],
                    "folder_name": save_info.get("folder_name", video_id),
                    "saved_files": [os.path.basename(f) for f in save_info["saved_files"]],
                }),
            })

        except Exception as e:
            event_queue.put({
                "step": "error",
                "message": str(e),
            })

        # Sentinel to signal stream termination
        event_queue.put(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    def event_stream():
        """Yield SSE events from the queue until worker is done."""
        while True:
            event = event_queue.get()
            if event is None:
                break
            yield _sse_event(event)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(data: dict) -> str:
    """Format a dict as a Server-Sent Event string."""
    return f"data: {json.dumps(data)}\n\n"


@app.route("/api/open-folder", methods=["POST"])
def open_folder():
    """Open the output folder in Windows File Explorer or native file manager."""
    data = request.get_json(silent=True) or {}
    folder_path = data.get("path")
    if not folder_path:
        video_id = data.get("video_id")
        if video_id:
            folder_path = os.path.join(get_app_dir(), "output", video_id)
        else:
            folder_path = os.path.join(get_app_dir(), "output")

    if folder_path and os.path.exists(folder_path):
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder_path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder_path])
            return {"status": "ok", "path": folder_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
    return {"status": "error", "message": f"Folder not found: {folder_path}"}, 404


@app.route("/api/history", methods=["GET"])
def history_list_api():
    """Return a list of all previously analyzed videos."""
    try:
        items = get_history_list()
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history/<video_id>", methods=["GET"])
def history_detail_api(video_id):
    """Return saved analysis outputs for a specific video."""
    try:
        item = get_history_item(video_id)
        if item:
            return jsonify(item)
        return jsonify({"error": "Video analysis not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history/<video_id>", methods=["DELETE"])
def history_delete_api(video_id):
    """Delete the analysis folder for a specific video."""
    try:
        success = delete_history_item(video_id)
        if success:
            return jsonify({"status": "ok", "deleted": video_id})
        return jsonify({"error": "Video folder not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    """Run the Flask app on the given host and port."""
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    print("\n  🎬 YouTube Video Analyzer — Web Interface")
    print("  ──────────────────────────────────────────")
    print("  Open http://127.0.0.1:5000 in your browser\n")
    run_server(debug=True)
