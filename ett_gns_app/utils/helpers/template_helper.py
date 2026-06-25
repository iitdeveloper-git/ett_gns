# services/utils/template_helper.py
import re
import os
import logging
from jinja2 import Environment, FileSystemLoader, TemplateError
from jinja2.meta import find_undeclared_variables

logger = logging.getLogger(__name__)


class TemplateHelper:
    def __init__(self, template_dir: str):
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.templates = self._discover_templates()
        logger.info(
            f"TemplateHelper initialized. Discovered {len(self.templates)} templates in '{self.template_dir}'"
        )

    def _discover_templates(self) -> dict:
        """Auto-discovers templates and their required variables."""
        discovered = {}
        if not os.path.exists(self.template_dir):
            logger.warning(f"Template directory '{self.template_dir}' does not exist.")
            return discovered

        for filename in os.listdir(self.template_dir):
            if filename.endswith(".html"):
                try:
                    with open(os.path.join(self.template_dir, filename), "r") as f:
                        source = f.read()

                    # Parse template to find variable names using Jinja meta
                    ast = self.env.parse(source)
                    variables = find_undeclared_variables(ast)
                    discovered[filename] = list(variables)
                except Exception as e:
                    logger.error(f"Error parsing template {filename}: {e}")

        return discovered

    def validate_template(self, template_name: str, data: dict) -> None:
        """
        Validates if the template is available and its required variables exist in the data.
        """
        logger.info(f"Validating template: {template_name}")

        if template_name not in self.templates:
            err = f"Template '{template_name}' is not available. Choose from: {', '.join(self.templates.keys())}."
            logger.error(err)
            raise ValueError(err)

        required_vars = self.templates[template_name]
        missing_vars = [var for var in required_vars if var not in data]
        if missing_vars:
            err = f"Missing variables for template '{template_name}': {', '.join(missing_vars)}."
            logger.warning(err)
            raise ValueError(err)

        logger.info(f"Template '{template_name}' validated successfully.")

    def render_template(self, template_name: str, data: dict) -> str:
        """Renders the template using Jinja2."""
        logger.info(f"Rendering template: {template_name}")
        try:
            template = self.env.get_template(template_name)
            rendered_content = template.render(data)
            logger.info(f"Template '{template_name}' rendered successfully.")
            return rendered_content
        except TemplateError as e:
            logger.error(f"Error rendering template '{template_name}': {str(e)}")
            raise ValueError(f"Error rendering template '{template_name}': {str(e)}")
