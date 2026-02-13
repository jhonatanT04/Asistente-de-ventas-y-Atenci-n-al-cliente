"""
Esquemas para el Guion recibido desde el Agente 2.

El Agente 2 procesa la entrada del usuario (texto, voz, imagen) y genera
un guión estructurado que incluye los códigos de barras de productos identificados.

Este guión es la entrada principal para el Agente 3 (nuestro sistema de ventas).
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal, List
from pydantic import BaseModel, Field


class ProductoEnGuion(BaseModel):
    """
    Producto identificado por el Agente 2.
    Contiene el código de barras que usaremos para buscar en nuestra BD.
    """
    codigo_barras: str = Field(
        description="Código de barras EAN/UPC del producto",
        examples=["7501234567890", "8806098934474"]
    )
    nombre_detectado: str = Field(
        description="Nombre del producto como lo identificó el Agente 2",
        examples=["Nike Air Zoom Pegasus 40", "Adidas Ultraboost Light"]
    )
    marca: Optional[str] = Field(
        default=None,
        description="Marca del producto",
        examples=["Nike", "Adidas", "Puma"]
    )
    categoria: Optional[str] = Field(
        default=None,
        description="Categoría del producto",
        examples=["running", "training", "lifestyle", "basketball"]
    )
    prioridad: Literal["alta", "media", "baja"] = Field(
        default="media",
        description="Prioridad basada en preferencias explícitas del usuario"
    )
    motivo_seleccion: str = Field(
        description="Por qué este producto fue seleccionado por el Agente 2",
        examples=[
            "Mencionado explícitamente por el usuario",
            "Alternativa similar al producto principal",
            "Opción con mejor relación calidad-precio"
        ]
    )


class PreferenciasUsuario(BaseModel):
    """Preferencias y necesidades del usuario extraídas por el Agente 2."""
    
    estilo_comunicacion: Literal["cuencano", "juvenil", "formal", "neutral"] = Field(
        default="neutral",
        description="Estilo de comunicación detectado del usuario"
    )
    
    uso_previsto: Optional[str] = Field(
        default=None,
        description="Para qué usará el producto",
        examples=["maratón", "gimnasio 3 veces por semana", "uso diario casual", "basketball"]
    )
    
    nivel_actividad: Optional[Literal["alto", "medio", "bajo"]] = Field(
        default=None,
        description="Nivel de actividad deportiva del usuario"
    )
    
    talla_preferida: Optional[str] = Field(
        default=None,
        description="Talla mencionada por el usuario",
        examples=["42", "9 US", "42.5"]
    )
    
    color_preferido: Optional[str] = Field(
        default=None,
        description="Color preferido mencionado",
        examples=["negro", "blanco", "azul marino"]
    )
    
    presupuesto_maximo: Optional[Decimal] = Field(
        default=None,
        description="Presupuesto máximo mencionado por el usuario"
    )
    
    busca_ofertas: bool = Field(
        default=False,
        description="Si el usuario mencionó explícitamente buscar descuentos/ofertas"
    )
    
    urgencia: Literal["alta", "media", "baja"] = Field(
        default="media",
        description="Qué tan urgente es la compra"
    )
    
    caracteristicas_importantes: List[str] = Field(
        default_factory=list,
        description="Características que el usuario mencionó como importantes",
        examples=[["amortiguación", "ligereza"], ["durabilidad"], ["estilo", "comodidad"]]
    )


class ContextoBusqueda(BaseModel):
    """Contexto adicional de la búsqueda."""
    
    tipo_entrada: Literal["texto", "voz", "imagen", "mixta"] = Field(
        description="Tipo de entrada procesada por el Agente 2"
    )
    
    producto_mencionado_explicitamente: bool = Field(
        default=False,
        description="Si el usuario mencionó un producto específico por nombre"
    )
    
    necesita_recomendacion: bool = Field(
        default=True,
        description="Si el usuario está indeciso o necesita ayuda para elegir"
    )
    
    intencion_principal: Literal["compra_directa", "comparar", "informacion", "recomendacion"] = Field(
        description="Intención principal detectada"
    )
    
    restricciones_adicionales: List[str] = Field(
        default_factory=list,
        description="Otras restricciones mencionadas",
        examples=["solo Nike", "no Adidas", "para pies planos"]
    )


class GuionEntrada(BaseModel):
    """
    Guion completo recibido del Agente 2.
    Este es el contrato de entrada principal para nuestro sistema.
    """
    
    # Identificación
    session_id: str = Field(
        description="ID de sesión único para seguimiento"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Momento en que se generó el guión"
    )
    
    # Productos identificados (mínimo 1, típicamente 2-3)
    productos: List[ProductoEnGuion] = Field(
        min_length=1,
        max_length=5,
        description="Lista de productos identificados con sus códigos de barras"
    )
    
    # Información del usuario
    preferencias: PreferenciasUsuario = Field(
        description="Preferencias y necesidades del usuario"
    )
    
    # Contexto
    contexto: ContextoBusqueda = Field(
        description="Contexto de la búsqueda"
    )
    
    # Textos originales para referencia
    texto_original_usuario: str = Field(
        description="Texto exacto/voz transcrita del usuario"
    )
    
    resumen_analisis: str = Field(
        description="Resumen ejecutivo del análisis del Agente 2",
        examples=[
            "Usuario busca zapatillas para maratón, presupuesto $150, talla 42. "
            "Interesado en Nike Pegasus o Air Max. Estilo cuencano."
        ]
    )
    
    # Metadata
    confianza_procesamiento: float = Field(
        ge=0.0, le=1.0,
        description="Confianza del Agente 2 en su análisis (0-1)"
    )
    
    def get_codigos_barras(self) -> List[str]:
        """Extrae todos los códigos de barras para búsqueda en BD."""
        return [p.codigo_barras for p in self.productos]
    
    def get_producto_prioritario(self) -> Optional[ProductoEnGuion]:
        """Retorna el producto con mayor prioridad."""
        if not self.productos:
            return None
        
        prioridad_orden = {"alta": 0, "media": 1, "baja": 2}
        return sorted(
            self.productos, 
            key=lambda p: prioridad_orden.get(p.prioridad, 1)
        )[0]


class GuionResponse(BaseModel):
    """
    Respuesta procesada por el Agente 3.
    Incluye la recomendación final con análisis comparativo.
    """
    
    success: bool
    mensaje: str
    
    # Análisis de productos encontrados
    productos_encontrados: List[dict] = Field(
        description="Productos de la BD que coinciden con los códigos de barras"
    )
    
    # Recomendación
    recomendacion_principal: dict = Field(
        description="Producto recomendado con justificación"
    )
    
    # Análisis comparativo
    comparacion: str = Field(
        description="Análisis detallado comparando las opciones"
    )
    
    # Sugerencias adicionales
    promociones_aplicables: List[str] = Field(
        default_factory=list,
        description="Códigos de promoción que aplican"
    )
    
    siguiente_paso: Literal["confirmar_compra", "mas_info", "ver_alternativas"] = Field(
        description="Qué sugerimos al usuario como siguiente paso"
    )
