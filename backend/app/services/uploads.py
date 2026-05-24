import uuid
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from ..config import settings

MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {"jpeg", "png", "webp"}
_FORMAT_TO_KIND = {"jpeg": "jpeg", "jpg": "jpeg", "png": "png", "webp": "webp"}


class UploadError(ValueError):
    pass


def upload_root() -> Path:
    root = settings.resolved_upload_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_path(relative_path: str) -> Path:
    root = upload_root().resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise UploadError("无效的文件路径")
    return path


def _image_kind(data: bytes) -> str:
    try:
        with Image.open(BytesIO(data)) as img:
            fmt = (img.format or "").lower()
    except (OSError, UnidentifiedImageError) as exc:
        raise UploadError("不支持的图片格式，请使用 JPEG、PNG 或 WebP") from exc
    kind = _FORMAT_TO_KIND.get(fmt)
    if kind not in ALLOWED:
        raise UploadError("不支持的图片格式，请使用 JPEG、PNG 或 WebP")
    return kind


def save_image(file: UploadFile | None, *, subdir: str) -> str | None:
    if file is None or not file.filename:
        return None
    data = file.file.read()
    if len(data) > MAX_BYTES:
        raise UploadError("图片过大，单张不超过 5MB")
    kind = _image_kind(data)
    ext = "jpg" if kind == "jpeg" else kind
    dest_dir = upload_root() / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    dest = dest_dir / name
    dest.write_bytes(data)
    try:
        with Image.open(dest) as img:
            img.thumbnail((1200, 1200))
            img.save(dest, optimize=True)
    except OSError as exc:
        dest.unlink(missing_ok=True)
        raise UploadError("无法读取图片文件") from exc
    return f"{subdir}/{name}"


def delete_stored_file(relative_path: str | None) -> None:
    if not relative_path:
        return
    path = _safe_path(relative_path)
    if path.is_file():
        path.unlink()
