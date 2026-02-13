"""
Base abstracta para todos los agentes del sistema.
"""
from abc import ABC, abstractmethod
from typing import Optional
from loguru import logger

from backend.domain.agent_schemas import AgentState, AgentResponse

# Clase base abstracta para todos los agentes
class BaseAgent(ABC):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        logger.info(f"Inicializando agente: {agent_name}")

    # Procesa el estado actual y retorna una respuesta.
    # Args: state: Estado actual de la conversación
    # Returns: AgentResponse con el mensaje y estado actualizado
    @abstractmethod
    async def process(self, state: AgentState) -> AgentResponse:
        pass

    # Determina si este agente puede manejar el estado actual.
    # Args: state: Estado actual de la conversación
    # Returns: True si el agente puede manejar este estado
    @abstractmethod
    def can_handle(self, state: AgentState) -> bool:
        
        pass

    def _add_to_history(
        self, state: AgentState, role: str, content: str
    ) -> AgentState:
        # Helper para agregar mensajes al historial.
        state.conversation_history.append({"role": role, "content": content})
        return state

    def _create_response(
        self,
        message: str,
        state: AgentState,
        should_transfer: bool = False,
        transfer_to: Optional[str] = None,
        **metadata,
    ) -> AgentResponse:
        # Helper para crear respuestas consistentes.
        state.current_agent = self.agent_name
        return AgentResponse(
            agent_name=self.agent_name,
            message=message,
            state=state,
            should_transfer=should_transfer,
            transfer_to=transfer_to,
            metadata=metadata,
        )
