import json
import re

import anthropic
from jinja2 import Environment, FileSystemLoader

from resume_builder.config import settings
from resume_builder.schema import ResumeContent


def _load_career_docs() -> tuple[str, str]:
    timeline = (settings.career_docs_dir / "01-career-timeline.md").read_text()
    skills = (settings.career_docs_dir / "02-skills-and-achievements.md").read_text()
    return timeline, skills


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if Claude includes them despite instructions."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _remove_em_dashes(content: ResumeContent) -> ResumeContent:
    """
    Post-processing safety net: strip em dashes from all free-text fields.
    Em dashes in company/role name fields are preserved (they're legitimate there).
    Replaces ' — ' (spaced) with ', ' and bare '—' with '-'.
    """
    data = content.model_dump()

    def clean(text: str) -> str:
        text = text.replace(" — ", ", ")
        text = text.replace("— ", ", ")
        text = text.replace(" —", ",")
        text = text.replace("—", "-")
        return text

    # Summary
    data["summary"] = clean(data["summary"])

    # Skill descriptions
    for cat in data["skills"]:
        cat["skills"] = clean(cat["skills"])

    # Bullet points only (preserve company and role fields)
    for role in data["experience"]:
        role["bullets"] = [clean(b) for b in role["bullets"]]

    return ResumeContent.model_validate(data)


def tailor_resume(
    job_description: str,
    timeline: str | None = None,
    skills_doc: str | None = None,
    candidate_name: str | None = None,
    candidate_email: str | None = None,
    candidate_phone: str | None = None,
    candidate_location: str | None = None,
    candidate_linkedin: str | None = None,
) -> ResumeContent:
    """Call Claude API with job description + career docs, return validated ResumeContent."""
    if timeline is None or skills_doc is None:
        timeline, skills_doc = _load_career_docs()

    env = Environment(loader=FileSystemLoader(str(settings.prompts_dir)))
    user_tmpl = env.get_template("user_template.txt")
    user_prompt = user_tmpl.render(
        job_description=job_description,
        career_timeline=timeline,
        skills_and_achievements=skills_doc,
        json_schema=json.dumps(ResumeContent.model_json_schema(), indent=2),
        candidate_name=candidate_name or settings.candidate_name,
        candidate_email=candidate_email or settings.candidate_email,
        candidate_phone=candidate_phone or settings.candidate_phone,
        candidate_location=candidate_location or settings.candidate_location,
        candidate_linkedin=candidate_linkedin or settings.candidate_linkedin,
    )

    system_prompt = (settings.prompts_dir / "system.txt").read_text()

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = _strip_markdown_fences(response.content[0].text)
    content = ResumeContent.model_validate_json(raw)
    return _remove_em_dashes(content)
