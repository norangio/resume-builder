import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from resume_builder.config import settings
from resume_builder.exporter import export_pdf
from resume_builder.renderer import render_html
from resume_builder.schema import ResumeContent
from resume_builder.tailor import tailor_resume

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a tailored PDF resume from your career docs and a job description."
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--jd", type=str, help="Job description as a string")
    input_group.add_argument("--jd-file", type=Path, help="Path to a .txt file with the job description")
    parser.add_argument(
        "--draft",
        type=Path,
        help="Skip the Claude step and render directly from an existing JSON draft",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output PDF path (default: output/resume_<timestamp>.pdf)",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Write HTML to output/ instead of PDF (useful for layout debugging)",
    )
    args = parser.parse_args()

    if not args.draft and not args.jd and not args.jd_file:
        console.print("[red]Provide --jd, --jd-file, or --draft.[/red]")
        parser.print_help()
        sys.exit(1)

    # ── Step 1: Get tailored content ──────────────────────────────────────────
    if args.draft:
        console.print(f"[cyan]Loading draft from {args.draft}[/cyan]")
        content = ResumeContent.model_validate_json(args.draft.read_text())
        console.print("[green]Draft loaded and validated.[/green]")
    else:
        job_description = args.jd or args.jd_file.read_text()
        console.print(f"[cyan]Calling Claude ({settings.model}) to tailor resume content...[/cyan]")
        content = tailor_resume(job_description)
        console.print("[green]Claude response received and validated.[/green]")

        # Write draft JSON for review
        settings.drafts_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_path = settings.drafts_dir / f"resume_draft_{timestamp}.json"
        draft_path.write_text(content.model_dump_json(indent=2))
        console.print(f"\n[bold]Draft written to:[/bold] {draft_path}")

        # ── Step 2: User review ───────────────────────────────────────────────
        console.print("\n[yellow]Review and edit the draft JSON before rendering.[/yellow]")
        console.print("[dim]You can change wording, add/remove bullets, reorder sections, etc.[/dim]")

        open_editor = Confirm.ask("Open draft in your default editor now?", default=True)
        if open_editor:
            subprocess.run(["open", str(draft_path)])

        Confirm.ask("\nDone editing? Press Enter to render the PDF", default=True)

        # Reload after edits
        content = ResumeContent.model_validate_json(draft_path.read_text())
        console.print("[green]Draft reloaded and validated.[/green]")

    # ── Step 3: Render HTML ───────────────────────────────────────────────────
    html = render_html(content)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    settings.output_dir.mkdir(exist_ok=True)

    if args.html_only:
        out_path = args.output or (settings.output_dir / f"resume_{timestamp}.html")
        out_path.write_text(html)
        console.print(f"\n[bold green]HTML saved to: {out_path}[/bold green]")
        console.print("[dim]Open in a browser to inspect layout before generating PDF.[/dim]")
        return

    # ── Step 4: Export PDF ────────────────────────────────────────────────────
    out_path = args.output or (settings.output_dir / f"resume_{timestamp}.pdf")
    console.print("[cyan]Rendering PDF...[/cyan]")
    export_pdf(html, out_path)
    console.print(f"\n[bold green]PDF saved to: {out_path}[/bold green]")

    open_pdf = Confirm.ask("Open PDF now?", default=True)
    if open_pdf:
        subprocess.run(["open", str(out_path)])


if __name__ == "__main__":
    main()
