"""
Dependencias de FastAPI para autenticación y autorización JWT.
Usa estas dependencias para proteger endpoints que requieren autenticación.
"""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError

from backend.config.security.config import settings
from backend.database.session import get_session
from backend.database.models.user_model import User
from sqlalchemy import select


security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """
    Valida el token JWT y retorna el payload del usuario.

    Uso en endpoints:
    ```python
    @router.get("/protected")
    async def protected_route(current_user: dict = Depends(get_current_user)):
        return {"user_id": current_user["id"], "username": current_user["username"]}
    ```

    Raises:
        HTTPException 401: Si el token es inválido, expirado o falta
    """
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("id")
        if user_id is None:
            raise credentials_exception
        return payload
    except InvalidTokenError:
        raise credentials_exception


async def get_current_active_user(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Valida que el usuario del token esté activo en la base de datos.

    Uso en endpoints:
    ```python
    @router.get("/protected")
    async def protected_route(user: dict = Depends(get_current_active_user)):
        return {"message": f"Hola {user['username']}"}
    ```

    Raises:
        HTTPException 403: Si el usuario está desactivado
        HTTPException 404: Si el usuario no existe
    """
    async with get_session() as session:
        query = select(User).where(User.id == current_user["id"])
        result = await session.execute(query)
        user: User | None = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario desactivado"
            )

    return current_user


async def require_admin(
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> dict:
    """
    Valida que el usuario tenga rol de administrador (role = 1).

    Uso en endpoints administrativos:
    ```python
    @router.delete("/users/{user_id}")
    async def delete_user(
        user_id: str,
        admin: dict = Depends(require_admin)
    ):
        # Solo administradores pueden acceder
        return {"deleted": user_id}
    ```

    Raises:
        HTTPException 403: Si el usuario no es administrador
    """
    if current_user.get("role") != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de administrador"
        )
    return current_user


async def require_client(
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> dict:
    """
    Valida que el usuario tenga rol de cliente (role = 2).

    Uso en endpoints de clientes:
    ```python
    @router.get("/my-orders")
    async def get_my_orders(client: dict = Depends(require_client)):
        return {"orders": [...]}
    ```

    Raises:
        HTTPException 403: Si el usuario no es cliente
    """
    if current_user.get("role") != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo clientes pueden acceder a este recurso"
        )
    return current_user
