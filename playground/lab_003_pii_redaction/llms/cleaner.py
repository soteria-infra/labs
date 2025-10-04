
import re

def clean_dirty_json(dirty_json_string: str) -> list:
    """
    A patch to the redacted json
    """
    data = re.sub(
        r'("\[REDACTED_PERSON_\d+]),\s*\n',
        r'\1",\n',
        dirty_json_string
    )


    return data