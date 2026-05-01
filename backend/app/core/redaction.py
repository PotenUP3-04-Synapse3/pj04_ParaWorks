import re

REDACTED_SECRET = '[redacted-secret]'

_SECRET_PATTERNS = (
    re.compile(r'xox[baprs]-\S+', flags=re.IGNORECASE),
    re.compile(r'(?<=token_ref=)\S+', flags=re.IGNORECASE),
    re.compile(r'(?<=refresh_token=)\S+', flags=re.IGNORECASE),
    re.compile(r'(?<=client_secret=)\S+', flags=re.IGNORECASE),
)


def redact_secret_text(value: str | None) -> str | None:
    if value is None:
        return None

    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(REDACTED_SECRET, redacted)
    return redacted
