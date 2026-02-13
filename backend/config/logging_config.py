"""
Configuración de Logging Estructurado con structlog.

Este módulo configura structlog para producir logs parseables en JSON
con contexto completo (session_id, agent, intent, etc.).

Características:
- Logs en JSON (parseable por ELK, Datadog, etc.)
- Context binding automático (session_id, agent_name, etc.)
- Timestamps en ISO8601
- Integración con loguru
- Desarrollo: Pretty print colorizado
- Producción: JSON compacto
"""
import os
import sys
import structlog
from structlog.types import EventDict, Processor
from typing import Any


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Agrega contexto de aplicación a cada log.

    Campos agregados:
    - app: Nombre de la aplicación
    - env: Ambiente (development, staging, production)
    - version: Versión de la app
    """
    event_dict["app"] = "sales-agent"
    event_dict["env"] = os.getenv("ENVIRONMENT", "development")
    event_dict["version"] = "3.0"
    return event_dict


def configure_structlog(json_logs: bool = None):
    """
    Configura structlog para la aplicación.

    Args:
        json_logs: Si True, usa formato JSON. Si None, detecta automáticamente
                   (JSON en producción, pretty print en desarrollo)
    """
    # Detectar si estamos en modo test
    is_testing = os.getenv("PYTEST_CURRENT_TEST") is not None or "pytest" in sys.modules
    
    # Detectar si usar JSON basado en ambiente
    if json_logs is None:
        environment = os.getenv("ENVIRONMENT", "development")
        json_logs = environment in ["production", "staging"] and not is_testing

    # Procesadores comunes para ambos formatos
    shared_processors: list[Processor] = [
        # Agrega timestamp en ISO8601
        structlog.processors.TimeStamper(fmt="iso"),

        # Agrega nivel de log
        structlog.stdlib.add_log_level,

        # NOTA: add_logger_name removido porque falla con PrintLogger
        # structlog.stdlib.add_logger_name,

        # Agrega contexto de aplicación
        add_app_context,

        # Captura stack traces en caso de excepciones
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_logs:
        # Producción: JSON compacto
        processors = shared_processors + [
            # Renderiza en JSON
            structlog.processors.JSONRenderer()
        ]
    else:
        # Desarrollo: Pretty print colorizado
        processors = shared_processors + [
            # Coloriza por nivel
            structlog.dev.ConsoleRenderer(
                colors=True,
                # Formatea excepciones de forma legible
                exception_formatter=structlog.dev.plain_traceback,
            )
        ]

    # Usar stdlib LoggerFactory en tests para evitar problemas con PrintLogger
    logger_factory = structlog.stdlib.LoggerFactory() if is_testing else structlog.PrintLoggerFactory(file=sys.stdout)
    
    structlog.configure(
        processors=processors,
        # Wrapper para stdlib logging
        wrapper_class=structlog.BoundLogger,
        # Context class que permite bind()
        context_class=dict,
        # Logger factory
        logger_factory=logger_factory,
        # Cache para performance (deshabilitar en tests)
        cache_logger_on_first_use=not is_testing,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Obtiene un logger configurado con structlog.

    Args:
        name: Nombre del logger (opcional, útil para identificar módulo)

    Returns:
        Logger estructurado listo para usar

    Ejemplo:
        >>> log = get_logger("orchestrator")
        >>> log.info("processing_query", query="Nike", session_id="user-123")

        # Producción (JSON):
        {
            "event": "processing_query",
            "query": "Nike",
            "session_id": "user-123",
            "timestamp": "2026-02-02T15:30:00Z",
            "level": "info",
            "logger": "orchestrator",
            "app": "sales-agent",
            "env": "production"
        }

        # Desarrollo (pretty):
        2026-02-02 15:30:00 [info     ] processing_query  query=Nike session_id=user-123
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


# Inicializar configuración al importar el módulo
configure_structlog()
