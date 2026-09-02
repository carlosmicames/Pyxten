"""
Regression cover for the applicant product.

The reviewer console must not disturb what is already in production. These tests
do not exercise business logic - they assert the surface: every applicant route
still exists, still requires authentication, and still refuses an anonymous
caller. That is the specific failure mode a new router mounted in the same app
could introduce.
"""
import pytest

# (method, path) for every applicant-facing endpoint, as mounted in main.py.
APPLICANT_ROUTES = [
    ("GET", "/projects"),
    ("POST", "/projects"),
    ("GET", "/projects/00000000-0000-0000-0000-000000000000"),
    ("GET", "/validations"),
    ("GET", "/validations/stats"),
    ("GET", "/validations/00000000-0000-0000-0000-000000000000"),
    ("GET", "/folders"),
    ("POST", "/folders"),
    ("GET", "/pcoc"),
    ("POST", "/pcoc"),
    ("GET", "/documents"),
    ("POST", "/documents"),
]


def test_health_and_root_are_public(client):
    assert client.get("/health").status_code == 200
    assert client.get("/").json()["service"] == "Pyxten API"


@pytest.mark.parametrize("method,path", APPLICANT_ROUTES)
def test_applicant_routes_still_exist_and_require_auth(client, method, path):
    """
    A 404 here would mean a route disappeared; a 200 would mean auth was lost.
    Anything else (401/403/422) means the route is present and guarded.
    """
    response = client.request(method, path, json={})
    assert response.status_code != 404, f"{method} {path} no longer exists"
    assert response.status_code in (401, 403, 422), (
        f"{method} {path} returned {response.status_code}; expected an auth failure"
    )


def test_document_requirements_endpoints_still_public(client):
    """These two feed the applicant checklist UI and take no auth."""
    pcoc = client.get("/documents/requirements/pcoc")
    permiso = client.get("/documents/requirements/permiso-unico")

    assert pcoc.status_code == 200
    assert permiso.status_code == 200
    assert len(pcoc.json()) > 0
    assert len(permiso.json()) > 0


def test_applicant_flow_still_uses_its_own_classifier(client):
    """
    The applicant use-classifier is deliberately left on OpenAI. This test exists
    so that "do not touch the applicant flow" is checkable rather than assumed.
    """
    import inspect

    from app.services import use_classifier

    source = inspect.getsource(use_classifier)
    assert "OpenAI" in source, "the applicant classifier was changed unexpectedly"
