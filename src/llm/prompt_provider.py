import os
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "llm/prompts"
)

_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_prompt(template_name: str, context: Dict[str, Any]) -> str:
    """
    Renders a template and returns the rendered content.

    Args:
        template_name (str): 'invoice_parser_system_prompt.jinja2' filename.
        context (Dict[str, Any]): variables to pass to the template.

    Returns:
        str: Rendered template content.
    """
    try:
        template = _jinja_env.get_template(template_name)
        return template.render(context)
    except Exception as e:
        raise RuntimeError(
            f"Jinja2 parse error ({template_name}): {str(e)}"
        )
