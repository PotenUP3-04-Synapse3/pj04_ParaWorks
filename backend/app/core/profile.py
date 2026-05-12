from pathlib import PurePosixPath
from urllib.parse import quote

PROFILE_AVATAR_EXTENSIONS = {
    'hanvv3@gmail.com': 'jpg',
    'hanvv3@koreacu.ac.kr': 'png',
    'kjw4work@gmail.com': 'jpg',
    'mina@paraworks.com': 'png',
    'yonghee199702@gmail.com': 'jpg',
}


def profile_avatar_url(email: str, role: str) -> str | None:
    normalized_email = email.strip().lower()
    if not normalized_email:
        return None

    extension = PROFILE_AVATAR_EXTENSIONS.get(normalized_email)
    if extension is None:
        return None

    filename = quote(f'{normalized_email}.{extension}')
    return str(PurePosixPath('/profile') / filename)
