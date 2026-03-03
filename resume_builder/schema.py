from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    name: str
    phone: str
    email: str
    location: str
    linkedin: str | None = None


class SkillCategory(BaseModel):
    category: str = Field(description="Skill category label, e.g. 'Biomanufacturing'")
    skills: str = Field(description="Comma-separated skills, e.g. 'cell therapy, biologics, GMP'")


class ExperienceEntry(BaseModel):
    company: str
    role: str
    start_date: str = Field(description="e.g. 'Sep 2024'")
    end_date: str = Field(description="e.g. 'Present' or 'Aug 2024'")
    location: str
    bullets: list[str] = Field(
        description="3-5 tailored bullet points, one sentence each, starting with an action verb"
    )


class EducationEntry(BaseModel):
    institution: str
    location: str
    degrees: list[str] = Field(description="e.g. ['M.S. Analytics / Data Science', 'B.S. Chemical Engineering']")


class ResumeContent(BaseModel):
    contact: ContactInfo
    summary: str = Field(
        description="2-3 sentence tailored professional summary written specifically for this job posting"
    )
    skills: list[SkillCategory] = Field(
        description="Ordered by relevance to the target job, most relevant category first"
    )
    experience: list[ExperienceEntry] = Field(
        description="Roles in reverse chronological order; omit roles with no meaningful relevance"
    )
    education: list[EducationEntry]
