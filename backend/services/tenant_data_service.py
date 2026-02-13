"""
Servicio de Datos Estáticos (Memoria RAG).
Lee los CSVs de políticas y FAQs para alimentar el contexto del Agente.
"""
from pathlib import Path
import pandas as pd
from loguru import logger
from dataclasses import dataclass

# Modelos simples para datos
@dataclass
class DocumentChunk:
    content: str
    category: str

class TenantDataService:
    @staticmethod
    async def read_chunks_csv() -> list[DocumentChunk]:
        """
        Lee el archivo 'chunks.csv' donde están tus políticas de envío/devolución.
        """
        # Ruta fija a tu carpeta de datos
        csv_path = Path("backend/data/app/chunks.csv")

        if not csv_path.exists():
            logger.warning(f"No encontró {csv_path}, la memoria estará vacía.")
            return []

        logger.info(f"Leyendo memoria desde: {csv_path}")
        df = pd.read_csv(csv_path)

        chunks = []
        for _, row in df.iterrows():
            # Convertimos cada fila del CSV en un objeto simple
            chunk = DocumentChunk(
                content=str(row.get("text", "")),     # Columna 'text' del CSV
                category=str(row.get("category", "")) # Columna 'category' del CSV
            )
            chunks.append(chunk)
            
        logger.info(f"Memoria cargada: {len(chunks)} documentos.")
        return chunks

    @staticmethod
    async def read_faqs_csv():
        """
        Lee FAQs simples
        """
        pass