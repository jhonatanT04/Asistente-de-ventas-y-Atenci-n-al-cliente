"""
Configuración de Rate Limiting para la API.
Define límites por endpoint y estrategias de rate limiting.
"""
from functools import wraps
from typing import Callable, Optional

from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# Crear limiter global
limiter = Limiter(key_func=get_remote_address)


class RateLimitConfig:
    """Configuración de rate limits por tipo de endpoint."""
    
    # Auth endpoints - más restrictivos por seguridad
    LOGIN = "5/minute"
    REGISTER = "3/minute"
    REFRESH_TOKEN = "10/minute"
    
    # GraphQL endpoints
    GRAPHQL_QUERY = "30/minute"
    GRAPHQL_MUTATION = "20/minute"
    
    # API endpoints
    HEALTH_CHECK = "100/minute"
    ROOT_ENDPOINT = "60/minute"
    LIST_PRODUCTS = "50/minute"
    
    # Order endpoints
    CREATE_ORDER = "10/minute"
    GET_ORDERS = "30/minute"
    CANCEL_ORDER = "5/minute"


def get_user_id_from_request(request: Request) -> Optional[str]:
    """
    Extrae el user_id del token JWT si está disponible.
    Usa esto para rate limiting por usuario en lugar de por IP.
    """
    try:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            # Decodificar token sin verificar expiración para rate limiting
            import jwt
            from backend.config.security.securityJWT import SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            return payload.get("id")
    except Exception:
        pass
    return None


def user_or_ip_key_func(request: Request) -> str:
    """
    Función de clave para rate limiting:
    - Usuarios autenticados: por user_id
    - Usuarios anónimos: por IP
    """
    user_id = get_user_id_from_request(request)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)


# Limiter por usuario (para endpoints donde importa la identidad)
user_limiter = Limiter(key_func=user_or_ip_key_func)


def apply_rate_limit(limit_string: str):
    """
    Decorador para aplicar rate limiting a funciones async.
    
    Args:
        limit_string: String de límite (ej: "5/minute", "100/hour")
    
    Usage:
        @apply_rate_limit("10/minute")
        async def my_endpoint(request: Request):
            return {"message": "Hello"}
    """
    def decorator(func: Callable) -> Callable:
        @limiter.limit(limit_string)
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def rate_limit_by_user(limit_string: str):
    """
    Decorador para rate limiting por usuario (o IP si no está autenticado).
    
    Args:
        limit_string: String de límite
    
    Usage:
        @rate_limit_by_user("20/minute")
        async def create_order(request: Request, user: User):
            return await process_order(user)
    """
    def decorator(func: Callable) -> Callable:
        @user_limiter.limit(limit_string)
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


class RateLimitHeaders:
    """Headers informativos sobre rate limiting."""
    
    LIMIT = "X-RateLimit-Limit"
    REMAINING = "X-RateLimit-Remaining"
    RESET = "X-RateLimit-Reset"
    RETRY_AFTER = "Retry-After"


def add_rate_limit_headers(
    response,
    limit: int,
    remaining: int,
    reset_time: int
):
    """Agrega headers informativos de rate limiting a la respuesta."""
    response.headers[RateLimitHeaders.LIMIT] = str(limit)
    response.headers[RateLimitHeaders.REMAINING] = str(remaining)
    response.headers[RateLimitHeaders.RESET] = str(reset_time)
    return response
