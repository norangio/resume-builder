"""FastAPI web app for the resume builder."""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, Form, Request
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
    has_career_docs,
    has_profile,
    load_career_docs,
    load_example_docs,
    load_profile,
    save_career_docs,
    save_profile,
)

app = FastAPI(title="Resume Builder")

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

# In-memory draft storage: {draft_id: {"content": ResumeContent, "username": str, "status": str}}
_drafts: dict[str, dict] = {}


def _render(template_name: str, **kwargs) -> HTMLResponse:
    template = jinja_env.get_template(template_name)
    return HTMLResponse(template.render(**kwargs))


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
    profile = data
    return _render(
        "profile.html",
        profile=profile,
        active_page="profile",
        flash_message="Profile saved.",
        flash_type="success",
    )


# --- Career Docs Setup ---


@app.get("/setup")
async def setup_page(username: str = Depends(get_current_user)):
    docs = load_career_docs(username)
    if docs:
        timeline, skills = docs
    else:
        timeline, skills = load_example_docs()
    return _render(
        "setup.html", timeline=timeline, skills=skills, active_page="setup"
    )


@app.post("/setup")
async def setup_save(
    username: str = Depends(get_current_user),
    timeline: str = Form(""),
    skills: str = Form(""),
):
    save_career_docs(username, timeline, skills)
    return _render(
        "setup.html",
        timeline=timeline,
        skills=skills,
        active_page="setup",
        flash_message="Career docs saved.",
        flash_type="success",
    )


# --- Generate ---


@app.get("/generate")
async def generate_page(username: str = Depends(get_current_user)):
    return _render(
        "generate.html",
        has_docs=has_career_docs(username),
        has_profile_data=has_profile(username),
        active_page="generate",
    )


def _run_generation(draft_id: str, username: str, jd: str) -> None:
    """Run Claude generation in background (called from a thread)."""
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

        # Save draft to disk as backup
        drafts_dir = settings.drafts_dir / username
        drafts_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_path = drafts_dir / f"resume_draft_{ts}.json"
        draft_path.write_text(content.model_dump_json(indent=2))

        _drafts[draft_id]["content"] = content
        _drafts[draft_id]["status"] = "ready"
    except Exception as e:
        _drafts[draft_id]["status"] = "error"
        _drafts[draft_id]["error"] = str(e)


@app.post("/generate")
async def generate_submit(
    username: str = Depends(get_current_user),
    jd: str = Form(""),
):
    if not jd.strip():
        return _render(
            "generate.html",
            has_docs=has_career_docs(username),
            has_profile_data=has_profile(username),
            active_page="generate",
            flash_message="Please paste a job description.",
            flash_type="error",
        )

    draft_id = str(uuid.uuid4())
    _drafts[draft_id] = {"username": username, "status": "generating", "content": None}

    # Run generation in a thread to avoid blocking
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_generation, draft_id, username, jd.strip())

    return _render("loading.html", draft_id=draft_id, active_page="generate")


@app.get("/poll/{draft_id}")
async def poll_draft(draft_id: str, username: str = Depends(get_current_user)):
    draft_info = _drafts.get(draft_id)

    if not draft_info or draft_info["username"] != username:
        return _render("error.html", error="Draft not found.", active_page="generate")

    if draft_info["status"] == "generating":
        return _render("loading.html", draft_id=draft_id, active_page="generate")

    if draft_info["status"] == "error":
        return _render(
            "error.html",
            error=f"Generation failed: {draft_info.get('error', 'Unknown error')}",
            active_page="generate",
        )

    return RedirectResponse(f"/review/{draft_id}", status_code=302)


# --- Review & Download ---


@app.get("/review/{draft_id}")
async def review_page(draft_id: str, username: str = Depends(get_current_user)):
    draft_info = _drafts.get(draft_id)

    if not draft_info or draft_info["username"] != username:
        return _render("error.html", error="Draft not found.", active_page="generate")

    if draft_info["status"] != "ready":
        return RedirectResponse(f"/poll/{draft_id}", status_code=302)

    content = draft_info["content"]
    return _render(
        "review.html",
        draft=content,
        draft_id=draft_id,
        active_page="generate",
    )


@app.post("/review/{draft_id}")
async def review_submit(
    draft_id: str,
    request: Request,
    username: str = Depends(get_current_user),
):
    draft_info = _drafts.get(draft_id)
    if not draft_info or draft_info["username"] != username:
        return _render("error.html", error="Draft not found.", active_page="generate")

    form = await request.form()

    # Rebuild ResumeContent from structured form fields
    profile = load_profile(username)

    contact = ContactInfo(
        name=profile.get("name", ""),
        email=profile.get("email", ""),
        phone=profile.get("phone", ""),
        location=profile.get("location", ""),
        linkedin=profile.get("linkedin") or None,
    )

    summary = form.get("summary", "")

    # Skills: parallel arrays of skill_category and skill_values
    categories = form.getlist("skill_category")
    values = form.getlist("skill_values")
    skills = [
        SkillCategory(category=cat.strip(), skills=val.strip())
        for cat, val in zip(categories, values)
        if cat.strip() and val.strip()
    ]

    # Experience: parse from hidden fields + bullet textareas
    exp_indices = form.getlist("exp_index")
    experience = []
    for idx in exp_indices:
        companies = form.getlist("exp_company")
        roles = form.getlist("exp_role")
        start_dates = form.getlist("exp_start_date")
        end_dates = form.getlist("exp_end_date")
        locations = form.getlist("exp_location")
        i = int(idx)

        bullets = [
            b.strip()
            for b in form.getlist(f"exp_bullet_{idx}")
            if b.strip()
        ]

        experience.append(
            ExperienceEntry(
                company=companies[i],
                role=roles[i],
                start_date=start_dates[i],
                end_date=end_dates[i],
                location=locations[i],
                bullets=bullets,
            )
        )

    # Education: parse from hidden fields
    edu_indices = form.getlist("edu_index")
    education = []
    for idx in edu_indices:
        institutions = form.getlist("edu_institution")
        edu_locations = form.getlist("edu_location")
        i = int(idx)
        degree_count = int(form.get(f"edu_degree_count_{idx}", "0"))
        degrees = [
            form.get(f"edu_degrees_{j}", "") for j in range(degree_count)
        ]
        education.append(
            EducationEntry(
                institution=institutions[i],
                location=edu_locations[i],
                degrees=[d for d in degrees if d],
            )
        )

    content = ResumeContent(
        contact=contact,
        summary=summary,
        skills=skills,
        experience=experience,
        education=education,
    )

    # Render HTML and export PDF
    html = render_html(content)

    output_dir = settings.output_dir / username
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = output_dir / f"resume_{ts}.pdf"

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, export_pdf, html, pdf_path)

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"resume_{ts}.pdf",
    )
