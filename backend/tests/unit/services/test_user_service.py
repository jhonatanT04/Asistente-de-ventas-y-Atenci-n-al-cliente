"""
Tests unitarios para UserService.
"""
import pytest
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.user_service import (
    UserService,
    UserAlreadyExistsError,
    UserNotFoundError
)
from backend.database.models import User


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserServiceCreate:
    """Tests para creación de usuarios."""
    
    async def test_create_user_success(
        self,
        clean_db: AsyncSession,
    ):
        """Test de creación exitosa de usuario."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from backend.database.session import get_engine
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        user, message = await user_service.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            full_name="Test User"
        )
        
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == 2  # Cliente por defecto
        assert user.is_active is True
        assert message == "Usuario creado exitosamente"
    
    async def test_create_user_duplicate_username(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de error al crear usuario con username duplicado."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        with pytest.raises(UserAlreadyExistsError):
            await user_service.create_user(
                username=test_user.username,  # Username existente
                email="otro@example.com",
                password="testpass123",
                full_name="Otro Usuario"
            )
    
    async def test_create_user_duplicate_email(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de error al crear usuario con email duplicado."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        with pytest.raises(UserAlreadyExistsError):
            await user_service.create_user(
                username="otrousuario",
                email=test_user.email,  # Email existente
                password="testpass123",
                full_name="Otro Usuario"
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserServiceQueries:
    """Tests para consultas de usuarios."""
    
    async def test_get_user_by_id(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de obtener usuario por ID."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        user = await user_service.get_user_by_id(test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.username == test_user.username
    
    async def test_get_user_by_username(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de obtener usuario por username."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        user = await user_service.get_user_by_username(test_user.username)
        
        assert user is not None
        assert user.username == test_user.username
    
    async def test_get_user_by_email(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de obtener usuario por email."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        user = await user_service.get_user_by_email(test_user.email)
        
        assert user is not None
        assert user.email == test_user.email
    
    async def test_list_users(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de listar usuarios."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        users = await user_service.list_users()
        
        assert len(users) >= 1
        assert any(u.id == test_user.id for u in users)
    
    async def test_list_users_by_role(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de listar usuarios filtrados por rol."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        # Filtrar por rol cliente (2)
        users = await user_service.list_users(role=2)
        
        assert all(u.role == 2 for u in users)


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserServiceUpdates:
    """Tests para actualizaciones de usuarios."""
    
    async def test_update_user(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de actualizar datos de usuario."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        user, message = await user_service.update_user(
            user_id=test_user.id,
            full_name="Nombre Actualizado"
        )
        
        assert user is not None
        assert user.full_name == "Nombre Actualizado"
        assert message == "Usuario actualizado exitosamente"
    
    async def test_change_password_success(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de cambio exitoso de contraseña."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        # Primero actualizar el password_hash del test_user
        from backend.config.security.securityJWT import hash_password
        test_user.password_hash = hash_password("oldpassword")
        await clean_db.commit()
        
        success, message = await user_service.change_password(
            user_id=test_user.id,
            old_password="oldpassword",
            new_password="newpassword123"
        )
        
        assert success is True
        assert message == "Contraseña cambiada exitosamente"
    
    async def test_change_password_wrong_old(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de cambio de contraseña con contraseña actual incorrecta."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        success, message = await user_service.change_password(
            user_id=test_user.id,
            old_password="wrongpassword",
            new_password="newpassword123"
        )
        
        assert success is False
        assert "incorrecta" in message.lower()


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserServiceStats:
    """Tests para estadísticas de usuarios."""
    
    async def test_get_user_stats(
        self,
        clean_db: AsyncSession,
        test_user: User
    ):
        """Test de obtener estadísticas."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        session_factory = async_sessionmaker(
            bind=clean_db.bind,
            expire_on_commit=False
        )
        user_service = UserService(session_factory)
        
        stats = await user_service.get_user_stats()
        
        assert "total_users" in stats
        assert "active_users" in stats
        assert stats["total_users"] >= 1
