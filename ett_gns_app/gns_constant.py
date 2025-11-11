class AllTemplatesData:
    def __init__(self):
        self.TEMPLATES = {
            "welcome_email.html": ["user_name", "welcome_message"],
            "password_reset.html": ["user_name", "reset_link"]
        }