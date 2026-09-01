from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import settings


security = HTTPBearer()

jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(jwks_url)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    token = credentials.credentials

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            options={
                "verify_aud": False,
            },
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token does not contain a user ID",
            )

        return UUID(user_id)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Authentication token has expired",
        )

    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid JWT: {error}",
        )

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID in token",
        )