"""
main.py - CLI entry point for the YouTube Video Analyzer.

Usage:
    python main.py <youtube_url_or_video_id> [--output-dir OUTPUT_DIR] [--include-transcript]

Example:
    python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
    python main.py dQw4w9WgXcQ --include-transcript
"""

import argparse
import sys
import os

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.transcript import extract_video_id, fetch_transcript, chunk_transcript
from src.generators import generate_steps, generate_mindmap, generate_flowchart
from src.utils import (
    save_output,
    create_markdown_report,
    save_all_analysis_documents,
    fetch_video_metadata,
)

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="🎬 YouTube Video Analyzer — Extract step-by-step procedures, "
        "mind maps, and flowcharts from any YouTube video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "  python main.py dQw4w9WgXcQ --no-steps --mindmap-only\n"
            "  python main.py dQw4w9WgXcQ --no-flowchart --output-dir my_reports\n"
        ),
    )
    parser.add_argument(
        "video",
        help="YouTube video URL or video ID",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to save outputs (default: output/)",
    )
    parser.add_argument(
        "--include-transcript",
        action="store_true",
        default=True,
        help="Include the raw transcript in the final report (default: True)",
    )
    parser.add_argument(
        "--no-transcript",
        action="store_true",
        help="Do not include the raw transcript in the final report",
    )
    parser.add_argument(
        "--no-steps",
        action="store_true",
        help="Skip generating the step-by-step procedure",
    )
    parser.add_argument(
        "--no-mindmap",
        action="store_true",
        help="Skip generating the mind map",
    )
    parser.add_argument(
        "--no-flowchart",
        action="store_true",
        help="Skip generating the flowchart",
    )
    parser.add_argument(
        "--steps-only",
        action="store_true",
        help="Generate only the step-by-step procedure",
    )
    parser.add_argument(
        "--mindmap-only",
        action="store_true",
        help="Generate only the mind map",
    )
    parser.add_argument(
        "--flowchart-only",
        action="store_true",
        help="Generate only the flowchart",
    )

    args = parser.parse_args()

    # Determine what to generate
    gen_steps = True
    gen_mindmap = True
    gen_flowchart = True
    include_transcript = True

    if args.steps_only or args.mindmap_only or args.flowchart_only:
        gen_steps = args.steps_only
        gen_mindmap = args.mindmap_only
        gen_flowchart = args.flowchart_only

    if args.no_steps:
        gen_steps = False
    if args.no_mindmap:
        gen_mindmap = False
    if args.no_flowchart:
        gen_flowchart = False
    if args.no_transcript:
        include_transcript = False

    if not gen_steps and not gen_mindmap and not gen_flowchart and not include_transcript:
        console.print("[red]❌ Error: All outputs are disabled. Please enable at least one output to generate.[/red]")
        sys.exit(1)

    console.print(
        Panel(
            "[bold cyan]🎬 YouTube Video Analyzer[/bold cyan]\n"
            "Extract structured insights from any YouTube video",
            border_style="cyan",
        )
    )

    # ── Step 1: Extract video ID & metadata ──
    try:
        video_id = extract_video_id(args.video)
        meta = fetch_video_metadata(video_id)
        video_title = meta.get("title", f"Video {video_id}")
        console.print(f"  📌 Video ID: [bold]{video_id}[/bold]")
        console.print(f"  🎬 Title:    [bold]{video_title}[/bold]")
        console.print(f"  👤 Author:   {meta.get('author', 'YouTube')}")
        selected_mods = []
        if gen_steps: selected_mods.append("Steps")
        if gen_mindmap: selected_mods.append("Mind Map")
        if gen_flowchart: selected_mods.append("Flowchart")
        if include_transcript: selected_mods.append("Transcript")
        console.print(f"  🎯 Outputs:  [green]{', '.join(selected_mods)}[/green]\n")
    except ValueError as e:
        console.print(f"  [red]❌ {e}[/red]")
        sys.exit(1)

    # ── Step 2: Fetch transcript ──
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching transcript...", total=None)
        try:
            transcript = fetch_transcript(video_id)
            chunks = chunk_transcript(transcript)
            progress.update(
                task,
                description=f"✅ Transcript fetched — {len(transcript)} chars, {len(chunks)} chunk(s)",
            )
        except Exception as e:
            progress.update(task, description=f"[red]❌ Failed to fetch transcript[/red]")
            console.print(f"  [red]Error: {e}[/red]")
            sys.exit(1)

    # ── Step 3: Generate selected outputs ──
    steps_output = ""
    mindmap_output = ""
    flowchart_output = ""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        if gen_steps:
            task = progress.add_task("🔍 Generating step-by-step procedure...", total=None)
            try:
                steps_output = generate_steps(transcript, chunks)
                progress.update(task, description="✅ Step-by-step procedure generated")
            except Exception as e:
                progress.update(task, description=f"[red]❌ Steps failed: {e}[/red]")
        else:
            console.print("  [dim]⚪ Steps: Skipped[/dim]")

        if gen_mindmap:
            task = progress.add_task("🧠 Generating mind map...", total=None)
            try:
                mindmap_output = generate_mindmap(transcript, chunks)
                progress.update(task, description="✅ Mind map generated")
            except Exception as e:
                progress.update(task, description=f"[red]❌ Mind map failed: {e}[/red]")
        else:
            console.print("  [dim]⚪ Mind Map: Skipped[/dim]")

        if gen_flowchart:
            task = progress.add_task("📊 Generating flowchart...", total=None)
            try:
                flowchart_output = generate_flowchart(transcript, chunks)
                progress.update(task, description="✅ Flowchart generated")
            except Exception as e:
                progress.update(task, description=f"[red]❌ Flowchart failed: {e}[/red]")
        else:
            console.print("  [dim]⚪ Flowchart: Skipped[/dim]")

    # ── Step 4: Save outputs using Video Title ──
    console.print("\n  [bold]📁 Saving Obsidian-ready Markdown documents with Video Title...[/bold]")

    transcript_text = transcript if include_transcript else ""
    save_info = save_all_analysis_documents(
        video_id=video_id,
        steps=steps_output,
        mindmap=mindmap_output,
        flowchart=flowchart_output,
        transcript=transcript_text,
        output_base_dir=args.output_dir,
        title=video_title,
    )

    for file_path in save_info["saved_files"]:
        filename = os.path.basename(file_path)
        console.print(f"    ✅ [green]{filename}[/green] → {file_path}")

    console.print(
        Panel(
            f"[bold green]✅ Analysis complete![/bold green]\n"
            f"Title: [bold]{video_title}[/bold]\n"
            f"Saved to: [cyan]{save_info['output_dir']}[/cyan]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
