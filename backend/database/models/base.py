"""
Base compartida para todos los modelos de SQLAlchemy.
TODOS los modelos deben importar Base desde este archivo.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa compartida para todos los modelos del sistema."""
    pass
