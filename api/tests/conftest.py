"""
Shared test fixtures.

The API has had no automated tests, so the first thing this suite has to earn is
the right to make changes safely: the applicant smoke tests below exist to prove
that adding the reviewer console did not disturb the product that is already in
production.

Nothing here talks to a real database, Supabase, Anthropic or OpenAI.
"""
import os
import sys
from pathlib import Path

import pytest

# Import the app package from /api regardless of where pytest was invoked.
API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

# Settings are read at import time, so these must be set before app.* is imported.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def reviewer_ctx():
    """
    A reviewer context whose data client is a stub.

    Routes are exercised against this rather than a live Supabase project, so the
    tests assert our behaviour - shaping, guardrails, audit writes - not
    PostgREST's.
    """
    from tests.stubs import StubSupabase
    from app.reviewer.context import ReviewerContext
    from uuid import UUID

    return ReviewerContext(
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        email="revisor@sanjuan.pr.gov",
        org_id="22222222-2222-2222-2222-222222222222",
        org_name="Municipio de San Juan",
        municipality="San Juan",
        role="reviewer",
        active_ruleset_id="33333333-3333-3333-3333-333333333333",
        org_config={"case_number_prefix": "SJ"},
        db=StubSupabase(),
    )
