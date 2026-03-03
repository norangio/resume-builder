# resume-builder

CLI tool that generates tailored, two-page PDF resumes using Claude. You provide your career history once, then for each job application Claude selects the most relevant experience, writes a custom summary, and reorders your skills — all output as a JSON draft you can review and edit before the final PDF is rendered.

## How It Works

1. You paste or provide a job description
2. Claude reads your career docs and produces a tailored JSON draft — selecting the most relevant bullets, writing a targeted summary, and reordering skills by relevance
3. You open the JSON draft, review and edit it (this is the human-in-the-loop step)
4. The tool renders it to HTML and exports a polished two-page PDF via headless Chromium

## Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) with access to the model you want to use (default: `claude-opus-4-6`)

**Note on API costs**: Each resume generation makes one Claude API call with your full career docs as context. With Opus, this typically costs $0.20–0.50 per run depending on how detailed your career docs are.

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/resume-builder.git
cd resume-builder

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e "."

# 4. Install Playwright browser (one-time)
playwright install chromium

# 5. Configure environment
cp .env.example .env
# Edit .env — see below
```

Open `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...   # Your Anthropic API key
CLAUDE_MODEL=claude-opus-4-6   # Or claude-sonnet-4-6 for faster/cheaper runs

CANDIDATE_NAME=Jane Smith
CANDIDATE_EMAIL=jane@example.com
CANDIDATE_PHONE=(555) 123-4567
CANDIDATE_LOCATION=San Francisco, CA
CANDIDATE_LINKEDIN=https://linkedin.com/in/janesmith   # optional
```

Your contact info is injected directly into the resume header — it's never sent to Claude. This keeps your personal details out of the API call.

## Create Your Career Docs

The tool reads two markdown files from the `career_docs/` directory. Example templates are provided to show the expected format:

```bash
# Copy the examples as a starting point
cp career_docs/01-career-timeline.example.md career_docs/01-career-timeline.md
cp career_docs/02-skills-and-achievements.example.md career_docs/02-skills-and-achievements.md
```

Then replace the placeholder content with your own:

**`01-career-timeline.md`** — Your full career history in reverse chronological order. For each role, include company, title, dates, location, and detailed bullet points. Be thorough — include more than you'd put on a single resume. Claude will select the most relevant items for each application.

**`02-skills-and-achievements.md`** — Your technical skills, domain expertise, notable achievements, education, and certifications. This complements the timeline with cross-cutting information that doesn't belong to a single role.

These files are gitignored (they contain personal info), but the `.example.md` templates are tracked so new users can see the expected structure.

## Usage

```bash
# Full workflow: Claude tailors → you review JSON → PDF rendered
python -m resume_builder.cli --jd "paste job description here"

# Or provide job description from a file
python -m resume_builder.cli --jd-file job.txt

# Re-render from an existing JSON draft (skips Claude — useful for editing and layout iteration)
python -m resume_builder.cli --draft drafts/resume_draft_20260219_120000.json

# Output HTML only (open in browser to iterate on layout without Playwright)
python -m resume_builder.cli --jd "..." --html-only

# Specify output path
python -m resume_builder.cli --jd "..." --output ~/Desktop/resume.pdf
```

## The JSON Draft

After Claude runs, it writes a JSON file to `drafts/`. This is the human-in-the-loop step — you can:
- Rewrite or trim any bullet
- Add bullets Claude missed
- Adjust the summary
- Reorder skills categories
- Remove a role entirely

The schema is straightforward and readable in any text editor. Once you confirm, the tool reloads the edited JSON and renders the PDF.

## Customization

**Visual style**: Edit `templates/resume.html.j2`. The template uses print-optimized CSS. Use `--html-only` to iterate quickly in your browser without running Playwright.

**Claude's selection behavior**: Edit `resume_builder/prompts/system.txt` to change how Claude picks bullets, writes summaries, or handles relevance.

**Claude model**: Set `CLAUDE_MODEL` in `.env` to use a different model (e.g. `claude-sonnet-4-6` for faster/cheaper runs).

## Project Structure

```
resume-builder/
├── career_docs/                  # Your career history (personal files gitignored)
│   ├── 01-career-timeline.example.md
│   └── 02-skills-and-achievements.example.md
├── resume_builder/
│   ├── cli.py                    # Entry point
│   ├── tailor.py                 # Claude API call + JSON validation
│   ├── schema.py                 # Pydantic models (resume data contract)
│   ├── renderer.py               # Jinja2 → HTML
│   ├── exporter.py               # Playwright HTML → PDF
│   ├── config.py                 # Settings from .env
│   └── prompts/
│       ├── system.txt            # Claude system prompt
│       └── user_template.txt     # User message template
├── templates/
│   └── resume.html.j2            # Resume HTML/CSS template
├── drafts/                       # Generated JSON drafts (gitignored)
└── output/                       # Generated PDFs (gitignored)
```

## License

[MIT](LICENSE)
