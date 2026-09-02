"""
Who is asking, and on behalf of which municipality.

Every reviewer route depends on `get_reviewer_context`. It resolves the caller's
organization from `org_members` and hands back a data client already bound to
their JWT. A route cannot reach reviewer data without going through here, and
what it reaches is limited by Postgres policies rather than by remembering to
add a filter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.auth import get_current_user
from app.reviewer.supa import SupabaseError, SupabaseUserClient, get_access_token
from app.schemas import UserInfo

# Roles, least to most privileged. Kept here so routes state their requirement
# by name instead of comparing strings inline.
ROLES = ("intake", "reviewer", "supervisor", "auditor")

# Who may change case data. An auditor can read everything and write nothing.
WRITE_ROLES = {"intake", "reviewer", "supervisor"}


@dataclass
class ReviewerContext:
    user_id: UUID
    email: Optional[str]
    org_id: str
    org_name: str
    municipality: str
    role: str
    active_ruleset_id: Optional[str]
    org_config: dict
    db: SupabaseUserClient

    @property
    def can_write(self) -> bool:
        return self.role in WRITE_ROLES

    def require_write(self) -> None:
        if not self.can_write:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Su rol permite consultar expedientes, pero no modificarlos.",
            )


def get_reviewer_context(
    user: UserInfo = Depends(get_current_user),
    token: str = Depends(get_access_token),
) -> Generator[ReviewerContext, None, None]:
    """
    FastAPI dependency. 403s anyone who is not a member of an organization, which
    is every applicant-side user - the reviewer console is invisible to them.
    """
    try:
        client = SupabaseUserClient(token)
    except SupabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"La consola del revisor no esta configurada: {exc}",
        )

    try:
        membership = client.select_one(
            "org_members",
            columns="org_id,role,organizations(id,name,municipality,active_ruleset_id,config)",
            filters={"user_id": f"eq.{user.user_id}"},
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Su cuenta no esta asociada a una oficina de permisos.",
            )

        org = membership.get("organizations") or {}

        yield ReviewerContext(
            user_id=user.user_id,
            email=user.email,
            org_id=membership["org_id"],
            org_name=org.get("name", ""),
            municipality=org.get("municipality", ""),
            role=membership["role"],
            active_ruleset_id=org.get("active_ruleset_id"),
            org_config=org.get("config") or {},
            db=client,
        )
    finally:
        client.close()
