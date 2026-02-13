"""
Cliente HTTP para Agente 2 - Reconocimiento de Productos (SIFT/ML).

Este cliente permite comunicarse con el servicio de reconocimiento de productos
que utiliza SIFT (Scale-Invariant Feature Transform) para identificar productos
por sus características visuales.

El Agente 2 corre en puerto 5000 y expone endpoints REST para:
- /predict: Identificar producto en imagen
- /register: Registrar nuevo producto con imagen
- /health: Health check del servicio
"""
import os
from typing import Optional
from decimal import Decimal

import httpx
import structlog

logger = structlog.get_logger()


class ProductRecognitionClient:
    """
    Cliente para el servicio de reconocimiento de productos del Agente 2.
    
    Este agente usa SIFT (Scale-Invariant Feature Transform) para
    identificar productos por sus características visuales.
    
    Attributes:
        base_url: URL base del servicio del Agente 2
        timeout: Timeout en segundos para las peticiones
        client: Cliente HTTP async de httpx
    
    Example:
        >>> client = ProductRecognitionClient()
        >>> result = await client.recognize_product(image_bytes, "photo.jpg")
        >>> print(result["product_name"])  # "Nike Air Zoom Pegasus 40"
        >>> await client.close()
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Inicializa el cliente del Agente 2.
        
        Args:
            base_url: URL del servicio. Por defecto usa AGENT2_URL del env o localhost:5000
            timeout: Timeout en segundos para las peticiones HTTP
        """
        self.base_url = (base_url or os.getenv("AGENT2_URL", "http://localhost:5000")).rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
        logger.info(
            "ProductRecognitionClient initialized",
            base_url=self.base_url,
            timeout=timeout
        )
    
    async def recognize_product(
        self,
        image_bytes: bytes,
        filename: str = "image.jpg"
    ) -> dict:
        """
        Identifica un producto a partir de una imagen.
        
        Envía la imagen al endpoint /predict del Agente 2 que utiliza
        SIFT para encontrar coincidencias con productos registrados.
        
        Args:
            image_bytes: Bytes de la imagen (JPEG, PNG, etc.)
            filename: Nombre del archivo para el content-type
            
        Returns:
            Dict con el resultado del reconocimiento:
            {
                "success": bool,           # True si se identificó el producto
                "product_name": str|None,  # Nombre del producto o None
                "matches": int,            # Número de keypoints coincidentes
                "confidence": float,       # Probabilidad (0.0 - 1.0)
                "error": str|None          # Mensaje de error si ocurre
            }
            
        Example:
            >>> with open("zapato.jpg", "rb") as f:
            ...     image_bytes = f.read()
            >>> result = await client.recognize_product(image_bytes, "zapato.jpg")
            >>> if result["success"]:
            ...     print(f"Producto: {result['product_name']}")
            ...     print(f"Confianza: {result['confidence']:.2%}")
        """
        try:
            logger.debug(
                "Sending image to Agent 2 for recognition",
                filename=filename,
                size_bytes=len(image_bytes)
            )
            
            # Preparar el archivo multipart
            files = {
                "image": (filename, image_bytes, "image/jpeg")
            }
            
            response = await self.client.post(
                f"{self.base_url}/predict",
                files=files
            )
            response.raise_for_status()
            
            data = response.json()
            logger.debug("Agent 2 response received", response=data)
            
            # El agente retorna "Unknown" si no encuentra coincidencias
            is_unknown = data.get("label") == "Unknown" or data.get("label") == "unknown"
            confidence = float(data.get("probability", 0.0))
            matches = int(data.get("matches", 0))
            
            # Éxito si NO es Unknown Y tiene suficiente confianza
            is_success = not is_unknown and confidence > 0.3 and matches > 5
            
            return {
                "success": is_success,
                "product_name": None if is_unknown else data.get("label"),
                "matches": matches,
                "confidence": confidence,
                "error": None
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error from Agent 2",
                status=e.response.status_code,
                response_text=e.response.text
            )
            return {
                "success": False,
                "product_name": None,
                "matches": 0,
                "confidence": 0.0,
                "error": f"Service error: {e.response.status_code}"
            }
            
        except httpx.ConnectError as e:
            logger.error(
                "Cannot connect to Agent 2",
                base_url=self.base_url,
                error=str(e)
            )
            return {
                "success": False,
                "product_name": None,
                "matches": 0,
                "confidence": 0.0,
                "error": "Agent 2 service is not available"
            }
            
        except Exception as e:
            logger.error("Error calling Agent 2", error=str(e), exc_info=True)
            return {
                "success": False,
                "product_name": None,
                "matches": 0,
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def register_product(
        self,
        image_bytes: bytes,
        product_name: str,
        filename: str = "image.jpg"
    ) -> dict:
        """
        Registra un nuevo producto con su imagen en el Agente 2.
        
        Este método entrena el modelo SIFT con una nueva imagen de producto
        para que pueda ser reconocido en futuras consultas.
        
        Args:
            image_bytes: Bytes de la imagen del producto
            product_name: Nombre del producto para asociar
            filename: Nombre del archivo
            
        Returns:
            Dict con el resultado del registro:
            {
                "success": bool,
                "message": str,
                "keypoints": int,  # Número de keypoints SIFT detectados
                "error": str|None
            }
        """
        try:
            logger.info(
                "Registering new product with Agent 2",
                product_name=product_name,
                filename=filename
            )
            
            files = {
                "image": (filename, image_bytes, "image/jpeg")
            }
            
            data = {
                "name": product_name
            }
            
            response = await self.client.post(
                f"{self.base_url}/register",
                files=files,
                data=data
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(
                "Product registered successfully",
                product_name=product_name,
                keypoints=result.get("keypoints", 0)
            )
            
            return {
                "success": True,
                "message": result.get("message", "Product registered"),
                "keypoints": result.get("keypoints", 0),
                "error": None
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error registering product",
                status=e.response.status_code,
                product_name=product_name
            )
            return {
                "success": False,
                "message": "",
                "keypoints": 0,
                "error": f"Service error: {e.response.status_code}"
            }
            
        except Exception as e:
            logger.error("Error registering product", error=str(e), exc_info=True)
            return {
                "success": False,
                "message": "",
                "keypoints": 0,
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        """
        Verifica si el servicio del Agente 2 está disponible.
        
        Returns:
            True si el servicio responde correctamente, False en caso contrario
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            is_healthy = response.status_code == 200
            logger.debug("Agent 2 health check", healthy=is_healthy)
            return is_healthy
        except Exception as e:
            logger.debug("Agent 2 health check failed", error=str(e))
            return False
    
    async def get_model_versions(self) -> dict:
        """
        Obtiene las versiones de modelos disponibles desde MLflow.
        
        Returns:
            Dict con información de versiones o error
        """
        try:
            response = await self.client.get(f"{self.base_url}/mlflow/versions")
            response.raise_for_status()
            return {
                "success": True,
                "versions": response.json(),
                "error": None
            }
        except Exception as e:
            logger.error("Error fetching model versions", error=str(e))
            return {
                "success": False,
                "versions": [],
                "error": str(e)
            }
    
    async def close(self):
        """
        Cierra la conexión HTTP.
        
        Es importante llamar a este método al finalizar para liberar recursos.
        """
        await self.client.aclose()
        logger.debug("ProductRecognitionClient closed")
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
