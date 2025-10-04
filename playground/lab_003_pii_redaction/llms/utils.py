import re


def clean_json_str(value: str) -> str:
    """
    A patch to the redacted JSON
    """
    return re.sub(r'("\[REDACTED_PERSON_\d+]),\s*\n', r'\1",\n', value)
