"""
Servicio de Gestión de Usuarios.

Maneja operaciones CRUD de usuarios, autenticación y gestión de perfiles.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from backend.config.logging_config import get_logger
from backend.config.security.securityJWT import hash_password, verify_password
from backend.database.models import User


class UserServiceError(Exception):
    """Excepción base para errores del servicio de usuarios."""
    pass


class UserNotFoundError(UserServiceError):
    """Error cuando no se encuentra un usuario."""
    pass


class UserAlreadyExistsError(UserServiceError):
    """Error cuando el usuario ya existe."""
    pass


class InvalidPasswordError(UserServiceError):
    """Error cuando la contraseña es inválida."""
    pass


class UserService:
    """
    Servicio para gestión completa de usuarios.
    
    Responsabilidades:
    - Crear usuarios (registro)
    - Consultar usuarios por ID, username, email
    - Actualizar perfiles
    - Cambiar contraseñas
    - Listar usuarios (admin)
    """
    
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.logger = get_logger("user_service")
    
    # ========================================================================
    # CREACIÓN DE USUARIOS
    # ========================================================================
    
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str,
        role: int = 2  # 2 = Cliente por defecto
    ) -> Tuple[User, str]:
        """
        Crea un nuevo usuario en el sistema.
        
        Args:
            username: Nombre de usuario único
            email: Correo electrónico único
            password: Contraseña en texto plano (se hashea)
            full_name: Nombre completo
            role: Rol del usuario (1=Admin, 2=Cliente)
            
        Returns:
            Tupla de (usuario_creado, mensaje)
            
        Raises:
            UserAlreadyExistsError: Si username o email ya existen
            UserServiceError: Por errores de BD
        """
        self.logger.info("Creando nuevo usuario", username=username, email=email)
        
        try:
            async with self.session_factory() as session:
                # Verificar si username ya existe
                existing = await session.execute(
                    select(User).where(User.username == username)
                )
                if existing.scalar_one_or_none():
                    raise UserAlreadyExistsError(f"Username '{username}' ya está en uso")
                
                # Verificar si email ya existe
                existing = await session.execute(
                    select(User).where(User.email == email)
                )
                if existing.scalar_one_or_none():
                    raise UserAlreadyExistsError(f"Email '{email}' ya está registrado")
                
                # Crear usuario
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True
                )
                
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                self.logger.info(
                    "Usuario creado exitosamente",
                    user_id=str(user.id),
                    username=username
                )
                
                return user, "Usuario creado exitosamente"
                
        except IntegrityError as e:
            self.logger.error(f"Error de integridad creando usuario: {e}")
            raise UserAlreadyExistsError("Username o email ya existen")
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error de BD creando usuario: {e}")
            raise UserServiceError("Error interno creando usuario")
    
    # ========================================================================
    # CONSULTAS
    # ========================================================================
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Obtiene un usuario por su ID.
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            El usuario encontrado o None
        """
        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error consultando usuario {user_id}: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Obtiene un usuario por su username.
        
        Args:
            username: Nombre de usuario
            
        Returns:
            El usuario encontrado o None
        """
        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    select(User).where(User.username == username)
                )
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error consultando usuario {username}: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Obtiene un usuario por su email.
        
        Args:
            email: Correo electrónico
            
        Returns:
            El usuario encontrado o None
        """
        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    select(User).where(User.email == email)
                )
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error consultando usuario por email {email}: {e}")
            return None
    
    async def list_users(
        self,
        role: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[User]:
        """
        Lista usuarios con filtros opcionales.
        
        Args:
            role: Filtrar por rol (1=Admin, 2=Cliente)
            is_active: Filtrar por estado activo
            limit: Cantidad máxima de resultados
            offset: Desplazamiento para paginación
            
        Returns:
            Lista de usuarios
        """
        try:
            async with self.session_factory() as session:
                query = select(User)
                
                if role is not None:
                    query = query.where(User.role == role)
                
                if is_active is not None:
                    query = query.where(User.is_active == is_active)
                
                query = query.order_by(User.created_at.desc())
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                return list(result.scalars().all())
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error listando usuarios: {e}")
            return []
    
    # ========================================================================
    # ACTUALIZACIONES
    # ========================================================================
    
    async def update_user(
        self,
        user_id: UUID,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[User, str]:
        """
        Actualiza los datos de un usuario.
        
        Args:
            user_id: ID del usuario a actualizar
            full_name: Nuevo nombre completo (opcional)
            email: Nuevo email (opcional)
            is_active: Nuevo estado (opcional)
            
        Returns:
            Tupla de (usuario_actualizado, mensaje)
            
        Raises:
            UserNotFoundError: Si el usuario no existe
            UserAlreadyExistsError: Si el email ya está en uso
        """
        try:
            async with self.session_factory() as session:
                user = await session.get(User, user_id)
                
                if not user:
                    raise UserNotFoundError(f"Usuario {user_id} no encontrado")
                
                # Verificar email único si se cambia
                if email and email != user.email:
                    existing = await session.execute(
                        select(User).where(User.email == email)
                    )
                    if existing.scalar_one_or_none():
                        raise UserAlreadyExistsError(f"Email '{email}' ya está registrado")
                    user.email = email
                
                if full_name:
                    user.full_name = full_name
                
                if is_active is not None:
                    user.is_active = is_active
                
                await session.commit()
                await session.refresh(user)
                
                self.logger.info(f"Usuario {user_id} actualizado exitosamente")
                return user, "Usuario actualizado exitosamente"
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error actualizando usuario {user_id}: {e}")
            raise UserServiceError("Error interno actualizando usuario")
    
    async def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Cambia la contraseña de un usuario.
        
        Args:
            user_id: ID del usuario
            old_password: Contraseña actual
            new_password: Nueva contraseña
            
        Returns:
            Tupla de (éxito, mensaje)
        """
        try:
            async with self.session_factory() as session:
                user = await session.get(User, user_id)
                
                if not user:
                    return False, "Usuario no encontrado"
                
                # Verificar contraseña actual
                if not verify_password(old_password, user.password_hash):
                    return False, "Contraseña actual incorrecta"
                
                # Actualizar contraseña
                user.password_hash = hash_password(new_password)
                await session.commit()
                
                self.logger.info(f"Contraseña cambiada para usuario {user_id}")
                return True, "Contraseña cambiada exitosamente"
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error cambiando contraseña: {e}")
            return False, "Error interno"
    
    async def reset_password(
        self,
        user_id: UUID,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Resetea la contraseña de un usuario (uso admin).
        
        Args:
            user_id: ID del usuario
            new_password: Nueva contraseña
            
        Returns:
            Tupla de (éxito, mensaje)
        """
        try:
            async with self.session_factory() as session:
                user = await session.get(User, user_id)
                
                if not user:
                    return False, "Usuario no encontrado"
                
                user.password_hash = hash_password(new_password)
                await session.commit()
                
                self.logger.info(f"Contraseña reseteada para usuario {user_id}")
                return True, "Contraseña reseteada exitosamente"
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error reseteando contraseña: {e}")
            return False, "Error interno"
    
    # ========================================================================
    # ELIMINACIÓN
    # ========================================================================
    
    async def delete_user(self, user_id: UUID) -> Tuple[bool, str]:
        """
        Elimina (desactiva) un usuario.
        
        Args:
            user_id: ID del usuario a eliminar
            
        Returns:
            Tupla de (éxito, mensaje)
        """
        try:
            async with self.session_factory() as session:
                user = await session.get(User, user_id)
                
                if not user:
                    return False, "Usuario no encontrado"
                
                # Soft delete - desactivar en lugar de eliminar
                user.is_active = False
                await session.commit()
                
                self.logger.info(f"Usuario {user_id} desactivado")
                return True, "Usuario desactivado exitosamente"
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error eliminando usuario {user_id}: {e}")
            return False, "Error interno"
    
    # ========================================================================
    # ESTADÍSTICAS
    # ========================================================================
    
    async def get_user_stats(self) -> dict:
        """
        Obtiene estadísticas de usuarios.
        
        Returns:
            Dict con estadísticas
        """
        try:
            async with self.session_factory() as session:
                total = await session.execute(select(User))
                total_count = len(total.scalars().all())
                
                active = await session.execute(
                    select(User).where(User.is_active == True)
                )
                active_count = len(active.scalars().all())
                
                admins = await session.execute(
                    select(User).where(User.role == 1)
                )
                admin_count = len(admins.scalars().all())
                
                clients = await session.execute(
                    select(User).where(User.role == 2)
                )
                client_count = len(clients.scalars().all())
                
                return {
                    "total_users": total_count,
                    "active_users": active_count,
                    "inactive_users": total_count - active_count,
                    "admin_users": admin_count,
                    "client_users": client_count
                }
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "inactive_users": 0,
                "admin_users": 0,
                "client_users": 0
            }
