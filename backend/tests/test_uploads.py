from io import BytesIO

import pytest
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.services import uploads


def _minimal_jpeg() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buf, format="JPEG")
    return buf.getvalue()


FAKE_JPEG = _minimal_jpeg()


def _upload_file(content: bytes, content_type: str, name: str = "photo.jpg") -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=name,
        headers=Headers({"content-type": content_type}),
    )


def test_save_image_writes_file(upload_root):
    path = uploads.save_image(_upload_file(FAKE_JPEG, "image/jpeg"), subdir="test")
    assert path is not None
    assert path.startswith("test/")
    assert (upload_root / path).is_file()


def test_save_image_none_returns_none(upload_root):
    assert uploads.save_image(None, subdir="test") is None


def test_rejects_invalid_mime(upload_root):
    with pytest.raises(uploads.UploadError, match="格式"):
        uploads.save_image(_upload_file(b"not-image", "text/plain"), subdir="test")


def test_rejects_oversized(upload_root):
    huge = FAKE_JPEG + b"\x00" * (6 * 1024 * 1024)
    with pytest.raises(uploads.UploadError, match="过大"):
        uploads.save_image(_upload_file(huge, "image/jpeg"), subdir="test")


def test_delete_file_removes(upload_root):
    path = uploads.save_image(_upload_file(FAKE_JPEG, "image/jpeg"), subdir="test")
    uploads.delete_stored_file(path)
    assert not (upload_root / path).exists()
