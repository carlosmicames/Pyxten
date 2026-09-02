"""
Test doubles.

`StubSupabase` mimics just enough of SupabaseUserClient to exercise the reviewer
services: it records what was written so a test can assert on the audit trail,
and it answers reads from an in-memory table map.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional


class StubSupabase:
    def __init__(self, tables: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self.tables: Dict[str, List[Dict[str, Any]]] = tables or {}
        self.uploads: List[tuple] = []
        self.signed: List[tuple] = []

    # -- helpers for assertions -------------------------------------------

    def rows(self, table: str) -> List[Dict[str, Any]]:
        return self.tables.setdefault(table, [])

    def audit_types(self) -> List[str]:
        return [row["event_type"] for row in self.rows("audit_events")]

    # -- the client surface under test ------------------------------------

    def _matches(self, row: Dict[str, Any], filters: Optional[Dict[str, str]]) -> bool:
        for column, expression in (filters or {}).items():
            value = str(row.get(column))

            if expression.startswith("eq."):
                if value != expression[3:]:
                    return False
            elif expression.startswith("like."):
                # PostgREST `like` uses % as the wildcard, same as SQL.
                import fnmatch

                pattern = expression[5:].replace("%", "*")
                if not fnmatch.fnmatchcase(value, pattern):
                    return False
            else:
                # Anything else should fail loudly rather than silently match.
                raise NotImplementedError(f"StubSupabase does not handle {expression!r}")
        return True

    def select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: Optional[Dict[str, str]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        found = [r for r in self.rows(table) if self._matches(r, filters)]
        return found[:limit] if limit else found

    def select_one(self, table: str, *, columns: str = "*", filters=None):
        found = self.select(table, columns=columns, filters=filters, limit=1)
        return found[0] if found else None

    def insert(self, table: str, rows: Any, *, returning: bool = True):
        batch = rows if isinstance(rows, list) else [rows]
        stored = []
        for row in batch:
            record = {"id": row.get("id") or str(uuid.uuid4()), **row}
            self.rows(table).append(record)
            stored.append(record)
        return stored if returning else []

    def update(self, table: str, *, filters: Dict[str, str], values: Dict[str, Any], returning: bool = True):
        updated = []
        for row in self.rows(table):
            if self._matches(row, filters):
                row.update(values)
                updated.append(row)
        return updated if returning else []

    def storage_upload(self, bucket: str, path: str, content: bytes, content_type: str = "application/pdf") -> str:
        self.uploads.append((bucket, path, len(content)))
        return path

    def storage_signed_url(self, bucket: str, path: str, expires_in: int = 300) -> str:
        self.signed.append((bucket, path, expires_in))
        return f"https://test.supabase.co/storage/v1/object/sign/{bucket}/{path}?token=stub"

    def storage_download(self, bucket: str, path: str) -> bytes:
        return b"%PDF-1.4 stub"

    def close(self) -> None:
        pass


def make_pdf(pages_text: List[str]) -> bytes:
    """
    A real, parseable PDF with the given text on each page.

    Built with pypdf + reportlab (both already production dependencies) so the
    extraction tests exercise the same code path a reviewer's upload would.
    """
    import io

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    for text in pages_text:
        # Wrap crudely; the tests care about characters extracted, not layout.
        y = 720
        for line in text.split("\n"):
            pdf.drawString(72, y, line[:95])
            y -= 14
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def blank_pdf(page_count: int = 2) -> bytes:
    """A PDF with pages but no text - stands in for a scan."""
    import io

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    for _ in range(page_count):
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()
