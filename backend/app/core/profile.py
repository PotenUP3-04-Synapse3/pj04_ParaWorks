from pathlib import PurePosixPath


def profile_avatar_url(email: str, role: str) -> str | None:
    if role == 'admin':
        return None

    local_part = email.split('@', 1)[0].strip().lower()
    if not local_part:
        return None

    filename = f'{local_part}.png'
    return str(PurePosixPath('/profile') / filename)
