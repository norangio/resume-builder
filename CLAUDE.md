# CLAUDE.md

Guidance for Claude Code when working in this project.

## What This Project Does

CLI tool that generates tailored, two-page PDF resumes from a user's career docs, customized to a specific job posting using Claude. The user is always in the loop — Claude produces a JSON draft they review and edit before the PDF is rendered.

## Architecture

```
job description (--jd or --jd-file)
      ↓
tailor.py  ←── career_docs/ (user's personal career history)
(Claude API)
      ↓
drafts/resume_draft_<timestamp>.json   ← user reviews and edits this
      ↓
renderer.py (Jinja2 → HTML)
      ↓
exporter.py (Playwright → PDF)
      ↓
output/resume_<timestamp>.pdf
```

## Key Files

| File | Purpose |
|------|---------|
| `resume_builder/schema.py` | Pydantic models — the contract between LLM output, user editing, and template rendering |
| `resume_builder/tailor.py` | Claude API call + JSON validation |
| `resume_builder/cli.py` | Entry point — run with `python -m resume_builder.cli` |
| `resume_builder/prompts/system.txt` | System prompt — edit this to tune Claude's selection behavior |
| `resume_builder/prompts/user_template.txt` | Jinja2 template for the user message sent to Claude |
| `templates/resume.html.j2` | HTML resume template — edit this to adjust visual layout |
| `resume_builder/config.py` | All paths and settings, loaded from `.env` |
| `career_docs/` | User's career history markdown files (gitignored; example templates tracked) |

## Environment Setup

Requires a `.env` file (copy from `.env.example`):
```
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-opus-4-6
CANDIDATE_NAME=Your Name
CANDIDATE_EMAIL=you@example.com
CANDIDATE_PHONE=(555) 000-0000
CANDIDATE_LOCATION=City, ST
```

Virtual environment: `.venv/` — activate with `source .venv/bin/activate` or prefix commands with `.venv/bin/`.

Playwright Chromium is already installed. If re-installing: `playwright install chromium`.

## Running the Tool

```bash
# Full workflow
python -m resume_builder.cli --jd "paste job description"
python -m resume_builder.cli --jd-file job.txt

# Re-render from existing JSON draft (skips Claude)
python -m resume_builder.cli --draft drafts/resume_draft_xyz.json

# HTML output only (for layout debugging — open in browser)
python -m resume_builder.cli --jd "..." --html-only
```

## Tuning Guidance

**If the PDF is overflowing to 3 pages**: Tighten `@page` margins in `templates/resume.html.j2`, reduce `font-size` on body or bullets, or reduce `line-height`. Also check that Claude isn't producing >5 bullets per role.

**If Claude's JSON doesn't parse**: The `_strip_markdown_fences()` function in `tailor.py` handles the common case of Claude wrapping output in ` ```json ``` `. If you're seeing other parse failures, print the raw response to debug.

**If bullet selection isn't relevant enough**: Edit `resume_builder/prompts/system.txt` — particularly the rules around relevance and omission.

**To change the visual style**: Edit `templates/resume.html.j2`. The blue accent color is `#1a5fa8`. Use `--html-only` to iterate quickly without Playwright.

## Important Constraints

- Resume must fit on exactly 2 pages — this is enforced via prompt instructions (max 5 bullets/role, max 5 roles) and CSS print rules
- Contact info is injected from `.env` config, never passed through Claude
- `output/` and `drafts/` are gitignored — PDFs and drafts don't get committed
- `career_docs/*.md` files are gitignored (personal info) — only `.example.md` templates are tracked
