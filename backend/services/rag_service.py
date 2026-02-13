"""
RAG Service - Retrieval Augmented Generation.
Sistema de búsqueda semántica profesional con ChromaDB + Vertex AI Embeddings.

Arquitectura:
1. Carga chunks.csv y faqs.csv al inicializar
2. Convierte textos en embeddings (vectores numéricos)
3. Almacena en ChromaDB (base de datos vectorial)
4. Búsqueda por similitud semántica cuando el usuario pregunta
5. Retorna documentos relevantes + metadata
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
from loguru import logger

from langchain_chroma import Chroma
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_core.documents import Document

from backend.config import get_business_settings


@dataclass
class RAGResult:
    """Resultado de búsqueda semántica."""
    content: str
    category: str
    relevance_score: float
    source: str  # "chunks" o "faqs"


class RAGService:
    """
    Servicio profesional de RAG con ChromaDB y Vertex AI.
    
    Features:
    - Embeddings con Vertex AI (text-embedding-004)
    - Persistencia en ChromaDB
    - Búsqueda semántica (no regex)
    - Metadata enriquecida
    - Logging detallado
    """
    
    def __init__(self):
        """Inicializa el servicio RAG."""
        logger.info(" Inicializando RAG Service...")
        
        settings = get_business_settings()
        
        # 1. Configurar embeddings de Vertex AI (usa GOOGLE_APPLICATION_CREDENTIALS de env)
        self.embeddings = VertexAIEmbeddings(
            model_name="text-embedding-004",
            project=settings.google_cloud_project,
            location=settings.google_location,
        )
        
        # 2. Rutas a los datos
        self.chunks_path = Path("backend/data/app/chunks.csv")
        self.faqs_path = Path("backend/data/app/faqs.csv")
        
        # 3. Directorio de persistencia para ChromaDB
        self.persist_directory = Path("backend/data/chromadb")
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # 4. Inicializar ChromaDB
        self.vectorstore = None
        self._initialize_vectorstore()
        
        logger.info(" RAG Service iniciado correctamente")
    
    def _initialize_vectorstore(self):
        """Carga o crea el vector store de ChromaDB."""
        
        # Intentar cargar vectorstore existente
        if (self.persist_directory / "chroma.sqlite3").exists():
            logger.info(" Cargando ChromaDB existente...")
            self.vectorstore = Chroma(
                collection_name="sneakerzone_knowledge",
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )
            logger.info(f" ChromaDB cargado: {self.vectorstore._collection.count()} documentos")
        else:
            logger.info(" Creando nuevo ChromaDB desde CSVs...")
            self._build_vectorstore_from_csvs()
    
    def _build_vectorstore_from_csvs(self):
        """Construye ChromaDB desde cero leyendo los CSVs."""
        
        documents = []
        
        # 1. Procesar chunks.csv
        if self.chunks_path.exists():
            logger.info(f" Leyendo {self.chunks_path}...")
            df_chunks = pd.read_csv(self.chunks_path)
            
            for _, row in df_chunks.iterrows():
                doc = Document(
                    page_content=row['text'],
                    metadata={
                        "category": row['category'],
                        "source": "chunks",
                        "type": "knowledge_base"
                    }
                )
                documents.append(doc)
            
            logger.info(f"Cargados {len(df_chunks)} chunks")
        else:
            logger.warning(f" No se encontró {self.chunks_path}")
        
        # 2. Procesar faqs.csv
        if self.faqs_path.exists():
            logger.info(f" Leyendo {self.faqs_path}...")
            df_faqs = pd.read_csv(self.faqs_path)
            
            for _, row in df_faqs.iterrows():
                # Para FAQs, combinamos la pregunta (patterns) con la respuesta
                patterns = row.get('patterns', '')
                response = row.get('response', '')
                category_faq = row.get('category', 'general')
                
                # Crear documento combinado
                combined_text = f"FAQ: {patterns}\nRespuesta: {response}"
                
                doc = Document(
                    page_content=combined_text,
                    metadata={
                        "category": category_faq,
                        "source": "faqs",
                        "type": "faq",
                        "response": response  # Guardamos la respuesta original
                    }
                )
                documents.append(doc)
            
            logger.info(f" Cargados {len(df_faqs)} FAQs")
        else:
            logger.warning(f" No se encontró {self.faqs_path}")
        
        # 3. Crear ChromaDB con todos los documentos
        if documents:
            logger.info(f" Generando embeddings para {len(documents)} documentos...")
            
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                collection_name="sneakerzone_knowledge",
                persist_directory=str(self.persist_directory)
            )
            
            logger.info(f" ChromaDB creado con {len(documents)} documentos")
        else:
            logger.error(" No se encontraron documentos para crear ChromaDB")
            raise ValueError("No hay documentos para el RAG")
    
    async def search(self, query: str, k: int = 3) -> List[RAGResult]:
        """
        Búsqueda semántica en la base de conocimiento.
        
        Args:
            query: Pregunta del usuario
            k: Número de resultados a retornar
        
        Returns:
            Lista de RAGResult ordenados por relevancia
        """
        logger.info(f" RAG Search: '{query}' (top-{k})")
        
        if not self.vectorstore:
            logger.error(" ChromaDB no inicializado")
            return []
        
        # Búsqueda semántica con scores
        results_with_scores = self.vectorstore.similarity_search_with_score(
            query,
            k=k
        )
        
        # Convertir a RAGResult
        rag_results = []
        for doc, score in results_with_scores:
            # ChromaDB usa distancia L2, menor score = más similar
            # Convertimos a relevancia (1 - normalizado)
            relevance = 1.0 / (1.0 + score)  # Score alto = relevante
            
            result = RAGResult(
                content=doc.page_content,
                category=doc.metadata.get("category", "unknown"),
                relevance_score=round(relevance, 3),
                source=doc.metadata.get("source", "unknown")
            )
            rag_results.append(result)
            
            logger.info(
                f" {result.source}/{result.category} "
                f"(score: {result.relevance_score})"
            )
        
        return rag_results
    
    async def get_context_for_query(self, query: str, max_results: int = 3) -> str:
        """
        Obtiene contexto relevante formateado para el LLM.
        
        Args:
            query: Pregunta del usuario
            max_results: Máximo de documentos a incluir
        
        Returns:
            String con contexto formateado listo para el prompt
        """
        results = await self.search(query, k=max_results)
        
        if not results:
            return "No se encontró información relevante en la base de conocimiento."
        
        # Formatear contexto
        context_parts = ["=== INFORMACIÓN RELEVANTE DE LA BASE DE CONOCIMIENTO ===\n"]
        
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"\n[Documento {i} - {result.category} | Relevancia: {result.relevance_score}]\n"
                f"{result.content}\n"
            )
        
        return "\n".join(context_parts)
    
    def rebuild_index(self):
        """Reconstruye el índice desde cero (útil si los CSVs cambian)."""
        logger.info(" Reconstruyendo índice RAG...")
        
        # Eliminar ChromaDB existente
        import shutil
        if self.persist_directory.exists():
            shutil.rmtree(self.persist_directory)
            self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Reconstruir
        self._build_vectorstore_from_csvs()
        logger.info(" Índice RAG reconstruido")
    
    def get_stats(self) -> Dict[str, int]:
        """Estadísticas del RAG."""
        if not self.vectorstore:
            return {"total_documents": 0}
        
        count = self.vectorstore._collection.count()
        
        return {
            "total_documents": count,
            "chunks_loaded": count // 2,  # Aproximado
            "faqs_loaded": count // 2,
            "embedding_model": "text-embedding-004",
            "vectorstore": "ChromaDB"
        }
