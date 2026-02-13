"""
Supabase JWT authentication (ES256 via JWKS)
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from jose.utils import base64url_decode
import requests
from uuid import UUID

from app.config import get_settings
from app.schemas import UserInfo

security = HTTPBearer()
settings = get_settings()

# Cache JWKS in memory (simple + effective)
_JWKS_CACHE = {"keys": None}


def _get_jwks():
    """
    Fetch Supabase JWKS (public keys used to verify ES256 tokens).
    """
    if _JWKS_CACHE["keys"] is not None:
        return _JWKS_CACHE["keys"]

    if not settings.supabase_url:
        raise RuntimeError("Missing SUPABASE_URL in environment variables")

    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    resp = requests.get(jwks_url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    _JWKS_CACHE["keys"] = data.get("keys", [])
    return _JWKS_CACHE["keys"]


def _get_unverified_header(token: str) -> dict:
    try:
        return jwt.get_unverified_header(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        )


def _find_jwk_by_kid(kid: str) -> dict:
    keys = _get_jwks()
    for k in keys:
        if k.get("kid") == kid:
            return k
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Signing key not found (kid mismatch)",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserInfo:
    """
    Verify Supabase JWT (ES256) and extract user info.
    """
    token = credentials.credentials

    try:
        header = _get_unverified_header(token)
        alg = header.get("alg")
        kid = header.get("kid")

        # Expect ES256 tokens from Supabase (new signing keys)
        if alg != "ES256":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: unsupported alg {alg}",
            )

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing kid",
            )

        jwk = _find_jwk_by_kid(kid)

        # Verify token
        # issuer for Supabase JWTs is typically: <SUPABASE_URL>/auth/v1
        issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"
        audience = getattr(settings, "supabase_jwt_aud", "authenticated")

        payload = jwt.decode(
            token,
            jwk,
            algorithms=["ES256"],
            audience=audience,
            issuer=issuer,
        )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID (sub)",
            )

        user_id = UUID(user_id_str)
        email = payload.get("email")

        return UserInfo(user_id=user_id, email=email)

    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth error: {str(e)}",
        )


def is_active_subscriber(user_id: UUID, db) -> bool:
    """
    Check if user has an active subscription (paid tier).
    Returns True if status is 'active' or 'trialing'.
    """
    from app.models import Subscription  # Import here to avoid circular import

    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not subscription:
        return False
    return subscription.status in {"active", "trialing"}


def require_active_subscription(user: UserInfo, db) -> None:
    """
    Dependency function to require active subscription.
    Raises HTTPException if user doesn't have active subscription.
    """
    if not is_active_subscriber(user.user_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere una suscripcion activa para acceder a esta funcion. Por favor actualice su plan.",
        )
