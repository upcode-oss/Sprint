from app.core.errors import APIError

ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def detect_image_mime(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9"):
        return "image/jpeg"
    if (
        content.startswith(b"\x89PNG\r\n\x1a\n")
        and content[12:16] == b"IHDR"
        and content.endswith(b"IEND\xaeB`\x82")
    ):
        return "image/png"
    if (
        len(content) >= 20
        and content[:4] == b"RIFF"
        and content[8:12] == b"WEBP"
        and content[12:16] in {b"VP8 ", b"VP8L", b"VP8X"}
        and int.from_bytes(content[4:8], "little") + 8 == len(content)
    ):
        return "image/webp"
    return None


def validate_image(
    content: bytes,
    claimed_mime_type: str | None,
    max_bytes: int,
    *,
    error_prefix: str,
    label: str,
) -> str:
    if not content:
        raise APIError(422, f"empty_{error_prefix}", f"{label} file is empty")
    if len(content) > max_bytes:
        raise APIError(
            413,
            f"{error_prefix}_too_large",
            f"{label} exceeds the configured size limit",
        )
    detected = detect_image_mime(content)
    if detected not in ALLOWED_IMAGE_MIME_TYPES or claimed_mime_type != detected:
        raise APIError(
            422,
            f"invalid_{error_prefix}",
            f"{label} must be a valid JPEG, PNG or WebP image",
        )
    return detected
