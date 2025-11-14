class AllTemplatesData:
    def __init__(self):
        self.TEMPLATES = {
            "welcome_email.html": ["user_name", "welcome_message"],
            "password_reset.html": ["user_name", "reset_link"],
            "universal_template.html": [
                "heading",
                "user_name",
                "body_message",
                "dynamic_block",
                "cta_url",
                "cta_label",
                "year",
            ]
        }