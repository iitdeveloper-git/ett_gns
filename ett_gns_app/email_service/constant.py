import re


# Valid email regex for recipient validation
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

def is_valid_email(email):
    """Check if the provided email is a valid format."""
    return re.match(EMAIL_REGEX, email) is not None
