from jinja2 import Environment, FileSystemLoader, select_autoescape

from resume_builder.config import settings
from resume_builder.schema import ResumeContent


def render_html(content: ResumeContent) -> str:
    env = Environment(
        loader=FileSystemLoader(str(settings.templates_dir)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("resume.html.j2")
    return template.render(**content.model_dump())
