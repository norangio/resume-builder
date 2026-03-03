from jinja2 import Environment, FileSystemLoader

from resume_builder.config import settings
from resume_builder.schema import ResumeContent


def render_html(content: ResumeContent) -> str:
    env = Environment(loader=FileSystemLoader(str(settings.templates_dir)))
    template = env.get_template("resume.html.j2")
    return template.render(**content.model_dump())
