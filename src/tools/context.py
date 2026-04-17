import json
import re
from pathlib import Path


def load_resume(resume_path: Path) -> str:
    """Read a .tex resume file and strip LaTeX commands for LLM consumption."""
    if not resume_path.exists():
        raise FileNotFoundError(f"Resume not found at {resume_path}")

    raw = resume_path.read_text(encoding="utf-8")
    cleaned = re.sub(r"\\[a-zA-Z]+\*?\{([^}]*)\}", r"\1", raw)
    cleaned = re.sub(r"\\[a-zA-Z]+\*?", "", cleaned)
    cleaned = re.sub(r"[{}]", "", cleaned)
    cleaned = re.sub(r"%.*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def load_projects(projects_path: Path) -> str:
    """Load projects.json and format as readable context string."""
    if not projects_path.exists():
        raise FileNotFoundError(f"Projects file not found at {projects_path}")

    with projects_path.open(encoding="utf-8") as f:
        projects: dict[str, str] = json.load(f)

    lines = [f"- {name}: {desc}" for name, desc in projects.items()]
    return "\n".join(lines)
