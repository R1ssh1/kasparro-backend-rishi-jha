"""
API Authentication Module

Provides API key authentication for protected endpoints.
"""
from fastapi import Header, HTTPException, status
from core.config import settings
import structlog

logger = structlog.get_logger(__name__)


async def verify_api_key(x_api_key: str = Header(..., description="API key for authentication")) -> str:
    """
    Verify API key from request header.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: 401 if API key is invalid or missing
    """
    if not settings.admin_api_key:
        logger.error("ADMIN_API_KEY not configured in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication not configured"
        )
    
    if x_api_key != settings.admin_api_key:
        logger.warning(
            "Invalid API key attempt",
            provided_key_prefix=x_api_key[:8] if x_api_key else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    return x_api_key


async def verify_api_key_optional(x_api_key: str = Header(None, description="Optional API key")) -> bool:
    """
    Optional API key verification for endpoints that support both auth and unauth access.
    
    Args:
        x_api_key: Optional API key from X-API-Key header
        
    Returns:
        True if authenticated, False if not provided
        
    Raises:
        HTTPException: 401 if API key is provided but invalid
    """
    if x_api_key is None:
        return False
    
    if x_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return True
