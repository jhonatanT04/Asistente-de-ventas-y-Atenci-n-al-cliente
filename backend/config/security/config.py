import os
from pathlib import Path
from dotenv import load_dotenv

# Buscar el archivo .env en el directorio del proyecto (raíz)
# Subir 3 niveles: config/security/ -> config/ -> backend/ -> raíz
env_path = Path(__file__).parent.parent.parent.parent / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    # Fallback: intentar cargar desde ruta por defecto
    load_dotenv(override=True)

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_HOURS", "24")) * 60

    if not SECRET_KEY:
        # Usar valor por defecto en desarrollo
        SECRET_KEY = "super-secret-sales-agent-key-2026-cuenca-dev-only"
        print("⚠️  SECRET_KEY no encontrada, usando valor por defecto para desarrollo")

settings = Settings()
