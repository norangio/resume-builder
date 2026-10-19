"""FastAPI web app for the resume builder."""

import asyncio
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader

from resume_builder.config import settings
from resume_builder.exporter import export_pdf
from resume_builder.renderer import render_html
from resume_builder.schema import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    ResumeContent,
    SkillCategory,
)
from resume_builder.tailor import tailor_resume

from web_app.auth import get_current_user
from web_app.user_data import (
    career_docs_are_example,
    has_career_docs,
    has_profile,
    list_drafts,
    load_career_docs,
    load_draft,
    load_example_docs,
    load_profile,
    save_career_docs,
    save_draft,
    save_profile,
)

app = FastAPI(title="Resume Builder")

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

# In-flight generations only: {draft_id: {"username", "status", "error", "started"}}.
# Finished drafts live on disk (see user_data.save_draft), so they survive restarts.
_jobs: dict[str, dict] = {}


def _render(template_name: str, **kwargs) -> HTMLResponse:
    template = jinja_env.get_template(template_name)
    return HTMLResponse(template.render(**kwargs))


def _jd_label(jd: str) -> str:
    """Short label for the drafts list: first non-empty line of the job description."""
    for line in jd.splitlines():
        line = line.strip()
        if line:
            return line[:90] + ("…" if len(line) > 90 else "")
    return "Untitled"


def _pdf_filename(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return f"{slug}_Resume.pdf" if slug else "Resume.pdf"


def _generate_context(username: str, **kwargs) -> dict:
    return {
        "has_docs": has_career_docs(username),
        "has_profile_data": has_profile(username),
        "drafts": list_drafts(username),
        "active_page": "generate",
        **kwargs,
    }


# --- Routes ---


@app.get("/")
async def index(username: str = Depends(get_current_user)):
    return RedirectResponse("/generate", status_code=302)


# --- Profile ---


@app.get("/profile")
async def profile_page(username: str = Depends(get_current_user)):
    profile = load_profile(username)
    return _render("profile.html", profile=profile, active_page="profile")


@app.post("/profile")
async def profile_save(
    username: str = Depends(get_current_user),
    name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    linkedin: str = Form(""),
):
    data = {
        "name": name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "location": location.strip(),
        "linkedin": linkedin.strip(),
    }
    save_profile(username, data)
    return _render(
        "profile.html",
        profile=data,
        active_page="profile",
        flash_message="Profile saved.",
        flash_type="success",
    )


# --- Career Docs Setup ---


@app.get("/setup")
async def setup_page(username: str = Depends(get_current_user)):
    docs = load_career_docs(username)
    is_example = docs is None or career_docs_are_example(*docs)
    timeline, skills = docs if docs else load_example_docs()
    return _render(
        "setup.html",
        timeline=timeline,
        skills=skills,
        is_example=is_example,
        active_page="setup",
    )


@app.post("/setup")
async def setup_save(
    username: str = Depends(get_current_user),
    timeline: str = Form(""),
    skills: str = Form(""),
):
    save_career_docs(username, timeline, skills)
    is_example = career_docs_are_example(timeline, skills)
    if is_example:
        flash_message, flash_type = (
            "Saved, but these are still the example docs. Replace them with your own history before generating.",
            "warning",
        )
    else:
        flash_message, flash_type = "Career docs saved.", "success"
    return _render(
        "setup.html",
        timeline=timeline,
        skills=skills,
        is_example=is_example,
        active_page="setup",
        flash_message=flash_message,
        flash_type=flash_type,
    )


# --- Generate ---


@app.get("/generate")
async def generate_page(username: str = Depends(get_current_user)):
    return _render("generate.html", **_generate_context(username))


def _run_generation(draft_id: str, username: str, jd: str) -> None:
    """Run Claude generation in a worker thread and save the draft to disk."""
    try:
        docs = load_career_docs(username)
        profile = load_profile(username)

        content = tailor_resume(
            job_description=jd,
            timeline=docs[0] if docs else None,
            skills_doc=docs[1] if docs else None,
            candidate_name=profile.get("name"),
            candidate_email=profile.get("email"),
            candidate_phone=profile.get("phone"),
            candidate_location=profile.get("location"),
            candidate_linkedin=profile.get("linkedin") or None,
        )
        save_draft(username, draft_id, content, label=_jd_label(jd))
        _jobs[draft_id]["status"] = "ready"
    except Exception as e:
        _jobs[draft_id]["status"] = "error"
        _jobs[draft_id]["error"] = str(e)


@app.post("/generate")
async def generate_submit(
    username: str = Depends(get_current_user),
    jd: str = Form(""),
):
    if not jd.strip():
        return _render(
            "generate.html",
            **_generate_context(
                username,
                flash_message="Please paste a job description.",
                flash_type="error",
            ),
        )
    if not has_career_docs(username) or not has_profile(username):
        return RedirectResponse("/generate", status_code=303)

    draft_id = str(uuid.uuid4())
    _jobs[draft_id] = {"username": username, "status": "generating", "started": datetime.now()}

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run_generation, draft_id, username, jd.strip())

    return RedirectResponse(f"/poll/{draft_id}", status_code=303)


@app.get("/poll/{draft_id}")
async def poll_draft(draft_id: str, username: str = Depends(get_current_user)):
    job = _jobs.get(draft_id)

    if job and job["username"] == username:
        if job["status"] == "generating":
            elapsed = int((datetime.now() - job["started"]).total_seconds())
            return _render("loading.html", draft_id=draft_id, elapsed=elapsed, active_page="generate")
        if job["status"] == "error":
            _jobs.pop(draft_id, None)
            return _render(
                "error.html",
                error=f"Generation failed: {job.get('error', 'Unknown error')}",
                active_page="generate",
            )
        _jobs.pop(draft_id, None)

    if load_draft(username, draft_id) is None:
        return _render("error.html", error="Draft not found.", active_page="generate")
    return RedirectResponse(f"/review/{draft_id}", status_code=302)


# --- Review & Download ---


def _content_from_form(form, username: str) -> ResumeContent:
    """Rebuild ResumeContent from the review form. Every field is keyed by its row index."""
    profile = load_profile(username)
    contact = ContactInfo(
        name=profile.get("name", ""),
        email=profile.get("email", ""),
        phone=profile.get("phone", ""),
        location=profile.get("location", ""),
        linkedin=profile.get("linkedin") or None,
    )

    def field(name: str) -> str:
        return str(form.get(name, "")).strip()

    skills = [
        SkillCategory(category=cat.strip(), skills=val.strip())
        for cat, val in zip(form.getlist("skill_category"), form.getlist("skill_values"))
        if cat.strip() and val.strip()
    ]

    experience = []
    for idx in form.getlist("exp_index"):
        bullets = [b.strip() for b in form.getlist(f"exp_{idx}_bullet") if b.strip()]
        experience.append(
            ExperienceEntry(
                company=field(f"exp_{idx}_company"),
                role=field(f"exp_{idx}_role"),
                start_date=field(f"exp_{idx}_start_date"),
                end_date=field(f"exp_{idx}_end_date"),
                location=field(f"exp_{idx}_location"),
                bullets=bullets,
            )
        )

    education = []
    for idx in form.getlist("edu_index"):
        degrees = [d.strip() for d in form.getlist(f"edu_{idx}_degree") if d.strip()]
        education.append(
            EducationEntry(
                institution=field(f"edu_{idx}_institution"),
                location=field(f"edu_{idx}_location"),
                degrees=degrees,
            )
        )

    return ResumeContent(
        contact=contact,
        summary=field("summary"),
        skills=skills,
        experience=experience,
        education=education,
    )


@app.get("/review/{draft_id}")
async def review_page(draft_id: str, username: str = Depends(get_current_user)):
    job = _jobs.get(draft_id)
    if job and job["username"] == username and job["status"] == "generating":
        return RedirectResponse(f"/poll/{draft_id}", status_code=302)

    content = load_draft(username, draft_id)
    if content is None:
        return _render("error.html", error="Draft not found.", active_page="generate")

    return _render("review.html", draft=content, draft_id=draft_id, active_page="generate")


@app.post("/review/{draft_id}")
async def review_submit(
    draft_id: str,
    request: Request,
    username: str = Depends(get_current_user),
):
    if load_draft(username, draft_id) is None:
        return _render("error.html", error="Draft not found.", active_page="generate")

    form = await request.form()
    content = _content_from_form(form, username)
    save_draft(username, draft_id, content)
    action = form.get("action", "pdf")

    if action == "save":
        return _render(
            "review.html",
            draft=content,
            draft_id=draft_id,
            active_page="generate",
            flash_message="Draft saved.",
            flash_type="success",
        )

    html = render_html(content)
    if action == "preview":
        return HTMLResponse(html)

    output_dir = settings.output_dir / username
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = output_dir / f"resume_{ts}_{draft_id[:8]}.pdf"

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, export_pdf, html, pdf_path)

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=_pdf_filename(content.contact.name),
    )
