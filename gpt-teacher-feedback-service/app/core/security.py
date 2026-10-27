from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

_api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(_api_key_header)) -> None:
    if not api_key or api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Internal-API-Key inválida ou ausente.",
        )
