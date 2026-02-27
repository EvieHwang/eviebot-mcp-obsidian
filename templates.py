"""Template listing and instantiation."""

from datetime import date, datetime

import notes
from vault import Vault


def list_templates(vault: Vault) -> str:
    """List available templates."""
    config = vault.templates_config
    folder = config["folder"]

    template_notes = list(vault.iter_notes(folder=folder))

    if not template_notes:
        return f"No templates found in {folder}/."

    lines = [f"Templates ({len(template_notes)}):"]
    for t in template_notes:
        lines.append(f"  - {t.stem}")
    return "\n".join(lines)


def create_from_template(
    vault: Vault, template: str, path: str, variables: dict | None = None
) -> str:
    """Create a new note from a template with variable substitution."""
    config = vault.templates_config
    folder = config["folder"]

    # Resolve template
    template_path = f"{folder}/{template}"
    resolved = vault.resolve_path(template_path)
    if resolved is None:
        return f"Error: Template not found: {template}"

    content = resolved.read_text(encoding="utf-8")

    # Built-in variable substitution
    today = date.today()
    now = datetime.now()
    dest_name = path.split("/")[-1].replace(".md", "")

    content = content.replace("{{date}}", str(today))
    content = content.replace("{{title}}", dest_name)
    content = content.replace("{{time}}", now.strftime("%H:%M"))

    # Custom variables
    if variables:
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))

    return notes.write_note(vault, path, content)
