import io
from uuid import uuid4

from fastapi.testclient import TestClient


def _create_type_and_asset(client: TestClient) -> str:
    r = client.post("/api/types", json={"name": "笔记本"})
    type_id = r.json()["id"]
    r = client.post(
        "/api/assets",
        json={"name": "X1", "type_id": type_id, "custom_data": {}},
    )
    return r.json()["id"]


def _upload(client: TestClient, asset_id: str, content: bytes, *, kind: str = "photo", filename: str = "a.jpg"):
    return client.post(
        f"/api/assets/{asset_id}/attachments",
        data={"kind": kind},
        files={"file": (filename, io.BytesIO(content), "image/jpeg")},
    )


class TestUploadEndpoint:
    def test_upload_returns_201_and_metadata(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = _upload(client, asset_id, b"fake-jpeg")
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["kind"] == "photo"
        assert data["size"] == len(b"fake-jpeg")
        assert data["mime_type"] == "image/jpeg"
        assert len(data["sha256"]) == 64
        assert data["original_name"] == "a.jpg"
        assert data["asset_id"] == asset_id

    def test_upload_to_missing_asset_404(self, client: TestClient):
        resp = _upload(client, str(uuid4()), b"x")
        assert resp.status_code == 404

    def test_upload_duplicate_same_content_409(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        _upload(client, asset_id, b"same")
        resp = _upload(client, asset_id, b"same")
        assert resp.status_code == 409


class TestListEndpoint:
    def test_list_empty(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = client.get(f"/api/assets/{asset_id}/attachments")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_newest_first(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        _upload(client, asset_id, b"first", filename="a.jpg")
        _upload(client, asset_id, b"second", filename="b.jpg")

        resp = client.get(f"/api/assets/{asset_id}/attachments")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        assert items[0]["original_name"] == "b.jpg"
        assert items[1]["original_name"] == "a.jpg"

    def test_list_missing_asset_404(self, client: TestClient):
        resp = client.get(f"/api/assets/{uuid4()}/attachments")
        assert resp.status_code == 404


class TestMetadataEndpoint:
    def test_get_returns_metadata(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        up = _upload(client, asset_id, b"abc").json()

        resp = client.get(f"/api/attachments/{up['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == up["id"]

    def test_get_missing_404(self, client: TestClient):
        resp = client.get(f"/api/attachments/{uuid4()}")
        assert resp.status_code == 404


class TestDownloadEndpoint:
    def test_download_returns_binary(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        content = b"binary-payload-123"
        up = _upload(client, asset_id, content).json()

        resp = client.get(f"/api/attachments/{up['id']}/content")
        assert resp.status_code == 200
        assert resp.content == content
        assert resp.headers["content-type"].startswith("image/jpeg")
        assert "attachment" in resp.headers["content-disposition"]
        assert "a.jpg" in resp.headers["content-disposition"]

    def test_download_missing_404(self, client: TestClient):
        resp = client.get(f"/api/attachments/{uuid4()}/content")
        assert resp.status_code == 404


class TestDeleteEndpoint:
    def test_delete_returns_204_and_removes(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        up = _upload(client, asset_id, b"xxx").json()

        resp = client.delete(f"/api/attachments/{up['id']}")
        assert resp.status_code == 204

        follow = client.get(f"/api/attachments/{up['id']}")
        assert follow.status_code == 404

    def test_delete_missing_404(self, client: TestClient):
        resp = client.delete(f"/api/attachments/{uuid4()}")
        assert resp.status_code == 404
