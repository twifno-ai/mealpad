from io import BytesIO

from PIL import Image


def _minimal_jpeg() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color="green").save(buf, format="JPEG")
    return buf.getvalue()


FAKE_JPEG = _minimal_jpeg()


def test_upload_cover(client):
    recipe = client.post(
        "/api/recipes",
        json={"name": "A", "type": "soup", "description": "", "ingredients": []},
    ).json()
    res = client.post(
        f"/api/recipes/{recipe['id']}/cover",
        files={"photo": ("x.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert res.status_code == 201
    got = client.get(f"/api/recipes/{recipe['id']}").json()
    assert got["cover_url"] is not None
    assert got["cover_url"].startswith("/uploads/")


def test_replace_cover_deletes_old(client, upload_root):
    recipe = client.post(
        "/api/recipes",
        json={"name": "B", "type": "meat", "description": "", "ingredients": []},
    ).json()
    first = client.post(
        f"/api/recipes/{recipe['id']}/cover",
        files={"photo": ("a.jpg", FAKE_JPEG, "image/jpeg")},
    ).json()
    first_path = first["cover_url"].removeprefix("/uploads/")
    client.post(
        f"/api/recipes/{recipe['id']}/cover",
        files={"photo": ("b.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert not (upload_root / first_path).exists()


def test_delete_cover(client):
    recipe = client.post(
        "/api/recipes",
        json={"name": "C", "type": "veg", "description": "", "ingredients": []},
    ).json()
    client.post(
        f"/api/recipes/{recipe['id']}/cover",
        files={"photo": ("x.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert client.delete(f"/api/recipes/{recipe['id']}/cover").status_code == 204
    got = client.get(f"/api/recipes/{recipe['id']}").json()
    assert got["cover_url"] is None


def test_invalid_cover_returns_400(client):
    recipe = client.post(
        "/api/recipes",
        json={"name": "D", "type": "other", "description": "", "ingredients": []},
    ).json()
    res = client.post(
        f"/api/recipes/{recipe['id']}/cover",
        files={"photo": ("x.txt", b"not-image", "text/plain")},
    )
    assert res.status_code == 400
