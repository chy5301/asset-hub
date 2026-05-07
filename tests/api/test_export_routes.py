"""GET /api/export router 测试. spec §2.1."""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestExportRoutes:
    def test_csv_200_with_bom_and_headers(self, client: TestClient, populated_db):
        resp = client.get("/api/export?format=csv")
        assert resp.status_code == 200
        assert resp.content.startswith(b"\xef\xbb\xbf")
        assert resp.headers["content-type"].startswith("text/csv")
        cd = resp.headers["content-disposition"]
        assert "attachment" in cd
        assert 'filename="assets-' in cd
        assert cd.endswith('.csv"')

    def test_xlsx_200_with_pk_magic_and_headers(self, client: TestClient, populated_db):
        resp = client.get("/api/export?format=xlsx")
        assert resp.status_code == 200
        assert resp.content.startswith(b"PK")
        assert resp.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        cd = resp.headers["content-disposition"]
        assert cd.endswith('.xlsx"')

    def test_missing_format_422(self, client: TestClient):
        resp = client.get("/api/export")
        assert resp.status_code == 422

    def test_invalid_format_422(self, client: TestClient):
        resp = client.get("/api/export?format=pdf")
        assert resp.status_code == 422

    def test_invalid_status_422(self, client: TestClient):
        resp = client.get("/api/export?format=csv&status=NOT_A_STATUS")
        assert resp.status_code == 422

    def test_filter_status_passed_through(self, client: TestClient, populated_db):
        # populated_db: 2 IDLE + 1 IN_USE + 1 RETIRED
        # filter status=IDLE → 仅 2 行 IDLE 资产 + header = 3 非空行
        resp = client.get("/api/export?format=csv&status=IDLE")
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        assert "在用" not in text  # IN_USE label 不应出现
        non_empty = [line for line in text.splitlines() if line.strip()]
        # 1 header + 2 IDLE = 3 行
        assert len(non_empty) == 3

    def test_filter_q_passed_through(self, client: TestClient, populated_db):
        resp = client.get("/api/export?format=csv&q=Stats笔记本-1")
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        assert "Stats笔记本-1" in text
        # 其他 3 个 stats 资产 (-2/-3/-4) 不应出现
        assert "Stats笔记本-2" not in text
        assert "Stats笔记本-3" not in text
        assert "Stats笔记本-4" not in text

    def test_zero_results_returns_header_only(self, client: TestClient):
        # 空 db (没 fixture 注入资产)
        resp = client.get("/api/export?format=csv")
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        non_empty = [line for line in text.splitlines() if line.strip()]
        assert len(non_empty) == 1  # 仅 header
