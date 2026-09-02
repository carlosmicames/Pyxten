"""
Supabase access on behalf of the signed-in user.

WHY THIS FILE EXISTS
--------------------
The rest of this API talks to Postgres through SQLAlchemy using DATABASE_URL,
which connects as the `postgres` role. That role bypasses Row Level Security, so
on those routes tenant isolation is only ever as good as the hand-written
`.filter(user_id == ...)` in each handler.

For the reviewer console that is not good enough: a reviewer in one municipality
must never be able to read another municipality's case, and "we remembered to
add the filter" is not a control you can show a government client.

So every reviewer route reaches the database through PostgREST carrying the
caller's own JWT. Postgres itself then applies the org_id policies from
migration 005. If a handler forgets to filter by org, the database returns
nothing anyway.

This is a deliberately small client - a few hundred lines of httpx over a
documented REST API - rather than a new SDK dependency, so the production deploy
gains no new version pins.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()

# PostgREST returns this SQLSTATE when a policy rejects a write.
_RLS_VIOLATION = "42501"


class SupabaseError(Exception):
    """Raised for transport-level problems; handlers convert these to HTTP errors."""


class SupabaseUserClient:
    """
    A thin PostgREST + Storage client bound to one user's access token.

    Every request carries:
      - `apikey`        the project's anon key (identifies the project)
      - `Authorization` the caller's JWT (identifies the person, and is what RLS reads)
    """

    def __init__(self, jwt: str, timeout: float = 30.0):
        settings = get_settings()

        if not settings.supabase_url:
            raise SupabaseError("SUPABASE_URL is not configured")
        if not settings.supabase_anon_key:
            raise SupabaseError("SUPABASE_ANON_KEY is not configured")

        self._base = settings.supabase_url.rstrip("/")
        self._jwt = jwt
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "apikey": settings.supabase_anon_key,
                "Authorization": f"Bearer {jwt}",
                "Accept": "application/json",
            },
        )

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SupabaseUserClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # -- internals ---------------------------------------------------------

    def _rest_url(self, table: str) -> str:
        return f"{self._base}/rest/v1/{table}"

    def _handle(self, response: httpx.Response, action: str) -> Any:
        if response.is_success:
            if response.status_code == 204 or not response.content:
                return []
            return response.json()

        # PostgREST error bodies look like {code, message, details, hint}
        try:
            body = response.json()
        except Exception:
            body = {"message": response.text}

        code = body.get("code")
        message = body.get("message", "")

        if response.status_code in (401, 403) or code == _RLS_VIOLATION:
            # Either the token is bad or a policy said no. Both are 403 to the
            # caller - we never disclose whether the row exists in another org.
            logger.warning("Supabase denied %s: %s %s", action, code, message)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a este recurso.",
            )

        logger.error(
            "Supabase error on %s: HTTP %s %s %s",
            action, response.status_code, code, message,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de base de datos al {action}.",
        )

    # -- table operations --------------------------------------------------

    def select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: Optional[Dict[str, str]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read rows.

        `filters` uses PostgREST syntax, e.g. {"case_id": "eq.<uuid>"}.
        RLS is applied by Postgres, so a row from another org simply is not returned.
        """
        params: Dict[str, Any] = {"select": columns}
        if filters:
            params.update(filters)
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = str(limit)

        response = self._client.get(self._rest_url(table), params=params)
        return self._handle(response, f"leer {table}")

    def select_one(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        rows = self.select(table, columns=columns, filters=filters, limit=1)
        return rows[0] if rows else None

    def insert(
        self,
        table: str,
        rows: Any,
        *,
        returning: bool = True,
    ) -> List[Dict[str, Any]]:
        prefer = "return=representation" if returning else "return=minimal"
        response = self._client.post(
            self._rest_url(table),
            content=json.dumps(rows if isinstance(rows, list) else [rows]),
            headers={"Content-Type": "application/json", "Prefer": prefer},
        )
        return self._handle(response, f"escribir en {table}")

    def update(
        self,
        table: str,
        *,
        filters: Dict[str, str],
        values: Dict[str, Any],
        returning: bool = True,
    ) -> List[Dict[str, Any]]:
        if not filters:
            # A filterless PATCH would rewrite every row the caller can see.
            raise SupabaseError("update() requires at least one filter")

        prefer = "return=representation" if returning else "return=minimal"
        response = self._client.patch(
            self._rest_url(table),
            params=filters,
            content=json.dumps(values),
            headers={"Content-Type": "application/json", "Prefer": prefer},
        )
        return self._handle(response, f"actualizar {table}")

    # -- storage -----------------------------------------------------------

    def storage_upload(
        self,
        bucket: str,
        path: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload an object and return its path. Storage RLS applies to the caller."""
        response = self._client.post(
            f"{self._base}/storage/v1/object/{bucket}/{path}",
            content=content,
            headers={"Content-Type": content_type, "x-upsert": "false"},
        )
        self._handle(response, f"subir el archivo a {bucket}")
        return path

    def storage_signed_url(self, bucket: str, path: str, expires_in: int = 300) -> str:
        """
        Mint a short-lived URL for reading one object.

        Nothing in this system hands out a durable link to a case document; a URL
        is created when someone with access asks for it and expires shortly after.
        """
        response = self._client.post(
            f"{self._base}/storage/v1/object/sign/{bucket}/{path}",
            content=json.dumps({"expiresIn": expires_in}),
            headers={"Content-Type": "application/json"},
        )
        body = self._handle(response, "generar el enlace del documento")

        signed = (body or {}).get("signedURL") or (body or {}).get("signedUrl")
        if not signed:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No se pudo generar el enlace del documento.",
            )
        return f"{self._base}/storage/v1{signed}" if signed.startswith("/") else signed

    def storage_download(self, bucket: str, path: str) -> bytes:
        response = self._client.get(f"{self._base}/storage/v1/object/{bucket}/{path}")
        if not response.is_success:
            self._handle(response, "descargar el archivo")
        return response.content


def get_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """The raw bearer token, which the reviewer data layer needs to act as the user."""
    return credentials.credentials
