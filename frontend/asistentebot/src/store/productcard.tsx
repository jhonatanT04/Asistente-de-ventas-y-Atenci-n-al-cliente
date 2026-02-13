// src/components/Store/ProductCard.tsx
import React, { useState } from 'react';
import type { Product } from '../services/graphqlservices';
import { FiShoppingCart, FiMapPin, FiPackage } from 'react-icons/fi';
import { getProductImageUrl } from '../utils/productImages';

interface ProductCardProps {
  product: Product;
  onAddToCart: (product: Product) => void;
  index: number;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, onAddToCart, index }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [imageError, setImageError] = useState(false);

  const isAvailable = product.stockStatus === 1 && product.quantityAvailable > 0;
  const isLowStock = product.quantityAvailable > 0 && product.quantityAvailable <= 5;

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isAvailable) {
      onAddToCart(product);
      
      // Feedback visual
      const button = e.currentTarget as HTMLButtonElement;
      button.style.transform = 'scale(0.9)';
      setTimeout(() => {
        button.style.transform = 'scale(1)';
      }, 100);
    }
  };

  // Animación de entrada escalonada
  const animationDelay = `${index * 0.03}s`;

  return (
    <article 
      className={`product-card ${!isAvailable ? 'out-of-stock' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ animationDelay }}
    >
      {/* Imagen del producto */}
      <div className="product-image-container">
        {!imageError ? (
          <img
            src={getProductImageUrl(product.barcode, product.id)}
            alt={product.productName}
            className="product-image"
            onError={() => setImageError(true)}
            loading="lazy"
          />
        ) : (
          <div className="product-image-placeholder">
            <FiPackage size={48} />
          </div>
        )}

        {/* Badge de stock */}
        {!isAvailable && (
          <div className="stock-badge out">AGOTADO</div>
        )}
        {isLowStock && isAvailable && (
          <div className="stock-badge low">ÚLTIMAS {product.quantityAvailable}</div>
        )}

        {/* Overlay hover */}
        <div className={`product-overlay ${isHovered ? 'visible' : ''}`}>
          <div className="overlay-content">
            <div className="overlay-info">
              <FiMapPin size={14} />
              <span>{product.warehouseLocation}</span>
            </div>
            {product.shelfLocation && (
              <div className="overlay-info">
                <FiPackage size={14} />
                <span>{product.shelfLocation}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Info del producto */}
      <div className="product-info">
        <div className="product-meta">
          <span className="product-batch">{product.batchNumber || 'N/A'}</span>
          <span className="product-stock">Stock: {product.quantityAvailable}</span>
        </div>

        <h3 className="product-name">{product.productName}</h3>

        <div className="product-footer">
          <div className="product-price">
            <span className="price-currency">$</span>
            <span>${Number(product.unitCost).toFixed(2)}</span>
          </div>

          <button
            className="add-to-cart-button"
            onClick={handleAddToCart}
            disabled={!isAvailable}
            aria-label={`Agregar ${product.productName} al carrito`}
          >
            <FiShoppingCart size={18} />
            <span className="button-text">Agregar</span>
          </button>
        </div>
      </div>
    </article>
  );
};

export default ProductCard;