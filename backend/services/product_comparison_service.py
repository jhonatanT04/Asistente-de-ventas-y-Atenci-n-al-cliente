"""
Servicio de Comparación y Recomendación de Productos.

Este servicio analiza los productos identificados por el Agente 2
y genera recomendaciones personalizadas basadas en las preferencias del usuario.
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from dataclasses import dataclass
from uuid import UUID

from loguru import logger

from backend.database.models import ProductStock
from backend.domain.guion_schemas import GuionEntrada, ProductoEnGuion, PreferenciasUsuario
from backend.domain.product_schemas import ProductComparisonSchema, ProductRecommendationResult


@dataclass
class ProductScore:
    """Score calculado para un producto."""
    product: ProductStock
    total_score: float
    reasons: List[str]
    matching_preferences: List[str]


class ProductComparisonService:
    """
    Servicio especializado en comparar productos y hacer recomendaciones.
    
    Responsabilidades:
    - Comparar productos del guión contra preferencias del usuario
    - Calcular scores de recomendación
    - Identificar la mejor opción
    - Generar justificaciones persuasivas
    """
    
    def __init__(self):
        self.logger = logger
    
    async def compare_and_recommend(
        self,
        products: List[ProductStock],
        guion: GuionEntrada
    ) -> ProductRecommendationResult:
        """
        Compara productos y genera una recomendación personalizada.
        
        Args:
            products: Productos encontrados en BD (de los códigos de barras)
            guion: Guion completo del Agente 2
            
        Returns:
            Resultado con comparación y recomendación
        """
        if not products:
            raise ValueError("No hay productos para comparar")
        
        # Crear diccionario de productos por código de barras
        products_by_barcode = {p.barcode: p for p in products if p.barcode}
        
        # Calcular scores para cada producto
        scored_products = []
        for producto_guion in guion.productos:
            product = products_by_barcode.get(producto_guion.codigo_barras)
            if product:
                score = self._calculate_product_score(
                    product, 
                    producto_guion, 
                    guion.preferencias
                )
                scored_products.append(score)
        
        if not scored_products:
            raise ValueError("Ningún producto del guión fue encontrado en BD")
        
        # Ordenar por score
        scored_products.sort(key=lambda x: x.total_score, reverse=True)
        
        # Crear schema de comparación
        comparison_products = []
        for sp in scored_products:
            comparison_products.append(ProductComparisonSchema(
                id=sp.product.id,
                product_name=sp.product.product_name,
                barcode=sp.product.barcode,
                brand=sp.product.brand,
                category=sp.product.category,
                unit_cost=sp.product.unit_cost,
                final_price=sp.product.final_price,
                savings_amount=sp.product.savings_amount,
                is_on_sale=sp.product.is_on_sale,
                discount_percent=sp.product.discount_percent,
                promotion_description=sp.product.promotion_description,
                quantity_available=sp.product.quantity_available,
                recommendation_score=sp.total_score,
                reason="; ".join(sp.reasons)
            ))
        
        # Mejor opción
        best = scored_products[0]
        
        # Generar reasoning detallado
        reasoning = self._generate_recommendation_reasoning(
            best, 
            scored_products[1:] if len(scored_products) > 1 else [],
            guion.preferencias
        )
        
        return ProductRecommendationResult(
            products=comparison_products,
            best_option_id=best.product.id,
            reasoning=reasoning,
            user_preferences_matched=best.matching_preferences
        )
    
    def _calculate_product_score(
        self,
        product: ProductStock,
        producto_guion: ProductoEnGuion,
        preferencias: PreferenciasUsuario
    ) -> ProductScore:
        """
        Calcula un score de 0-100 para un producto basado en preferencias.
        """
        score = 0.0
        reasons = []
        matched_prefs = []
        
        # 1. Prioridad del Agente 2 (hasta 25 puntos)
        prioridad_scores = {"alta": 25, "media": 15, "baja": 5}
        score += prioridad_scores.get(producto_guion.prioridad, 10)
        if producto_guion.prioridad == "alta":
            reasons.append("Producto de alta prioridad según tus preferencias")
            matched_prefs.append("producto_preferido")
        
        # 2. Precio y Presupuesto (hasta 25 puntos)
        if preferencias.presupuesto_maximo:
            if product.final_price <= preferencias.presupuesto_maximo:
                score += 25
                reasons.append(f"Precio dentro de tu presupuesto (${product.final_price})")
                matched_prefs.append("precio")
            elif product.final_price <= preferencias.presupuesto_maximo * Decimal("1.1"):
                score += 15
                reasons.append(f"Precio ligeramente superior pero con buena relación calidad-precio")
            else:
                score += 5
                reasons.append(f"Precio superior a tu presupuesto pero con características premium")
        else:
            score += 15  # Sin presupuesto definido, precio neutro
        
        # 3. Descuentos y Promociones (hasta 20 puntos)
        if product.is_on_sale and product.has_active_promotion:
            score += 20
            ahorro = product.savings_amount
            reasons.append(f"🎉 En OFERTA: Ahorras ${ahorro:.2f}")
            if product.promotion_description:
                reasons.append(f"Promoción: {product.promotion_description}")
            matched_prefs.append("descuento")
        elif product.is_on_sale:
            score += 15
            reasons.append(f"Descuento disponible")
        
        # 4. Stock disponible (hasta 15 puntos)
        if product.quantity_available > 10:
            score += 15
        elif product.quantity_available > 5:
            score += 10
            reasons.append("Stock limitado - ¡popular!")
        elif product.quantity_available > 0:
            score += 5
            reasons.append(f"¡Solo quedan {product.quantity_available} unidades!")
        else:
            score -= 20  # Penalizar si no hay stock
            reasons.append("Sin stock disponible")
        
        # 5. Uso previsto y categoría (hasta 15 puntos)
        if preferencias.uso_previsto and product.category:
            uso_lower = preferencias.uso_previsto.lower()
            categoria_lower = product.category.lower() if product.category else ""
            
            # Running
            if "correr" in uso_lower or "maratón" in uso_lower or "running" in uso_lower:
                if "run" in categoria_lower:
                    score += 15
                    reasons.append(f"Ideal para {preferencias.uso_previsto}")
                    matched_prefs.append("uso_previsto")
                elif "training" in categoria_lower:
                    score += 8
            
            # Gimnasio
            elif "gym" in uso_lower or "gimnasio" in uso_lower:
                if "train" in categoria_lower or "gym" in categoria_lower:
                    score += 15
                    reasons.append(f"Perfecto para entrenamiento en gimnasio")
                    matched_prefs.append("uso_previsto")
            
            # Casual
            elif "casual" in uso_lower or "caminar" in uso_lower:
                if "life" in categoria_lower or "casual" in categoria_lower:
                    score += 15
                    reasons.append(f"Excelente para uso casual diario")
                    matched_prefs.append("uso_previsto")
        
        # 6. Color preferido (hasta 5 puntos) - basado en nombre del producto
        if preferencias.color_preferido:
            color_lower = preferencias.color_preferido.lower()
            nombre_lower = product.product_name.lower()
            if color_lower in nombre_lower:
                score += 5
                reasons.append(f"Disponible en tu color preferido: {preferencias.color_preferido}")
                matched_prefs.append("color")
        
        # 7. Talla (5 puntos si coincide)
        if preferencias.talla_preferida:
            # Aquí asumimos que el stock general indica disponibilidad
            # En un sistema real verificaríamos stock por talla específica
            score += 5
        
        # Asegurar rango 0-100
        score = max(0.0, min(100.0, score))
        
        return ProductScore(
            product=product,
            total_score=round(score, 1),
            reasons=reasons,
            matching_preferences=matched_prefs
        )
    
    def _generate_recommendation_reasoning(
        self,
        best: ProductScore,
        others: List[ProductScore],
        preferencias: PreferenciasUsuario
    ) -> str:
        """
        Genera un análisis simple de por qué el producto es la mejor opción.
        Texto plano sin formato markdown ni emojis excesivos.
        """
        partes = []
        
        # Producto recomendado
        partes.append(f"Recomendación: {best.product.product_name}")
        
        # Precio de forma simple
        if best.product.is_on_sale:
            partes.append(
                f"Precio: ${best.product.final_price:.2f} "
                f"(antes ${best.product.unit_cost:.2f}, "
                f"ahorras ${best.product.savings_amount:.2f})"
            )
            if best.product.promotion_description:
                partes.append(f"Promoción: {best.product.promotion_description}")
        else:
            partes.append(f"Precio: ${best.product.final_price:.2f}")
        
        # Razones principales
        if best.reasons:
            razones_texto = ". ".join(best.reasons[:3])
            partes.append(f"Razones: {razones_texto}")
        
        # Comparación simple con alternativas
        if others:
            otra = others[0]
            diff = otra.product.final_price - best.product.final_price
            if diff > 0:
                partes.append(
                    f"Comparado con {otra.product.product_name}: "
                    f"este ahorra ${diff:.2f}"
                )
        
        # Stock si es bajo
        if best.product.quantity_available <= 5:
            partes.append(f"Stock: Solo {best.product.quantity_available} unidades disponibles")
        
        return " ".join(partes)
    
    def format_product_for_chat(
        self,
        product: ProductStock,
        is_recommended: bool = False
    ) -> str:
        """
        Formatea un producto para mostrar en el chat.
        """
        lines = []
        
        if is_recommended:
            lines.append(f"🏆 **{product.product_name}** ⭐ RECOMENDADO")
        else:
            lines.append(f"• **{product.product_name}**")
        
        # Precio
        if product.is_on_sale:
            lines.append(f"  💰 ~~${product.unit_cost:.2f}~~ → **${product.final_price:.2f}**")
            lines.append(f"  🎉 Ahorras: ${product.savings_amount:.2f}")
            if product.promotion_description:
                lines.append(f"  🎁 {product.promotion_description}")
        else:
            lines.append(f"  💰 ${product.final_price:.2f}")
        
        # Stock
        if product.quantity_available > 10:
            lines.append(f"  ✅ Stock disponible")
        elif product.quantity_available > 3:
            lines.append(f"  ⚡ Solo {product.quantity_available} unidades")
        else:
            lines.append(f"  🔥 ¡Últimas {product.quantity_available} unidades!")
        
        return "\n".join(lines)
