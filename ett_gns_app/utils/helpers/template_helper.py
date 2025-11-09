# services/utils/template_helper.py
from jinja2 import Environment, FileSystemLoader, TemplateError
from ett_gns_app.gns_constant import AllTemplatesData
from ett_gns_app.utils.helpers.logger import setup_logger
# Set up the logger
logger = setup_logger()

class TemplateHelper:
    def __init__(self, template_dir):
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.templates = AllTemplatesData().TEMPLATES
        logger.info("TemplateHelper initialized with template directory: %s", self.template_dir)

    def validate_template(self, template_name, data):
        """
        Validates if the template is available and its required variables exist in the data.
        :param template_name: The name of the template (e.g., 'welcome_email.html')
        :param data: Dictionary containing the dynamic variables for the template
        """
        logger.info("Validating template: %s", template_name)

        if template_name not in self.templates:
            logger.error("Template '%s' is not available.", template_name)
            raise ValueError(f"Template '{template_name}' is not available. Choose from: {', '.join(self.templates.keys())}.")
        
        required_vars = self.templates[template_name]
        missing_vars = [var for var in required_vars if var not in data]
        if missing_vars:
            logger.warning("Missing variables for template '%s': %s", template_name, ', '.join(missing_vars))
            raise ValueError(f"Missing variables for template '{template_name}': {', '.join(missing_vars)}.")

        logger.info("Template '%s' validated successfully.", template_name)

    def render_template(self, template_name, data):
        """
        Renders the template using Jinja2.
        :param template_name: The name of the template (e.g., 'welcome_email.html')
        :param data: Dictionary with dynamic data to populate the template
        :return: Rendered HTML content
        """
        logger.info("Rendering template: %s", template_name)
        try:
            template = self.env.get_template(template_name)
            rendered_content = template.render(data)
            logger.info("Template '%s' rendered successfully.", template_name)
            return rendered_content
        except TemplateError as e:
            logger.error("Error rendering template '%s': %s", template_name, str(e))
            raise ValueError(f"Error rendering template '{template_name}': {str(e)}")