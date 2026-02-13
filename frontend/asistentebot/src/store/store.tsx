// src/components/Store/Store.tsx
import React, { useState, useEffect } from 'react';
import { productService } from '../services/graphqlservices';
import type { Product } from '../services/graphqlservices';
import ProductCard from './productcard';
import './store.css';
import { FiShoppingCart, FiSearch, FiX } from 'react-icons/fi';

const Store: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [cartCount, setCartCount] = useState(0);
  const [searchFocused, setSearchFocused] = useState(false);

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    filterProducts();
  }, [searchTerm, products]);

  const loadProducts = async () => {
    try {
      setIsLoading(true);
      // Llamada a GraphQL listProducts
      const data = await productService.listProducts(100);
      
      // Transformar datos de GraphQL a formato del componente
      const transformedProducts: Product[] = data.map(p => ({
        id: p.id,
        productName: p.productName,
        unitCost: p.unitCost,
        quantityAvailable: p.quantityAvailable,
        stockStatus: p.stockStatus,
        warehouseLocation: p.warehouseLocation,
        shelfLocation: p.shelfLocation || '',
        batchNumber: p.batchNumber || '',
        barcode: p.barcode
      }));

      setProducts(transformedProducts);
      setFilteredProducts(transformedProducts);
    } catch (error) {
      console.error('Error cargando productos:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const filterProducts = () => {
    if (!searchTerm.trim()) {
      setFilteredProducts(products);
      return;
    }

    const term = searchTerm.toLowerCase();
    const filtered = products.filter(p =>
      p.productName.toLowerCase().includes(term) ||
      (p.batchNumber && p.batchNumber.toLowerCase().includes(term)) ||
      (p.warehouseLocation && p.warehouseLocation.toLowerCase().includes(term))
    );

    setFilteredProducts(filtered);
  };

  const handleAddToCart = (product: Product) => {
    setCartCount(prev => prev + 1);
    console.log('Producto agregado al carrito:', product.productName);
    // TODO: Implementar lógica completa del carrito
  };

  const clearSearch = () => {
    setSearchTerm('');
    setSearchFocused(false);
  };

  const availableCount = filteredProducts.filter(p => p.stockStatus === 1).length;
  const outOfStockCount = filteredProducts.filter(p => p.stockStatus === 0).length;

  if (isLoading) {
    return (
      <div className="store-loading">
        <div className="loading-spinner"></div>
        <p className="loading-text">Cargando inventario...</p>
      </div>
    );
  }

  return (
    <div className="store-container">
      {/* Header Minimalista */}
      <header className="store-header">
        <div className="header-grid">
          <div className="brand">
            <h1 className="store-title">SNEAKER<br/>ZONE</h1>
            <p className="store-subtitle">CUENCA · ECUADOR</p>
          </div>

          <div className="header-stats">
            <div className="stat">
              <span className="stat-value">{filteredProducts.length}</span>
              <span className="stat-label">Productos</span>
            </div>
            <div className="stat">
              <span className="stat-value">{availableCount}</span>
              <span className="stat-label">Disponibles</span>
            </div>
          </div>

          <button className="cart-button" aria-label="Carrito de compras">
            <FiShoppingCart />
            {cartCount > 0 && <span className="cart-count">{cartCount}</span>}
          </button>
        </div>
      </header>

      {/* Search Bar con animación */}
      <div className="search-section">
        <div className={`search-wrapper ${searchFocused ? 'focused' : ''}`}>
          <FiSearch className="search-icon" />
          <input
            type="text"
            placeholder="Buscar por modelo, marca o ubicación..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            className="search-input"
          />
          {searchTerm && (
            <button 
              className="search-clear" 
              onClick={clearSearch}
              aria-label="Limpiar búsqueda"
            >
              <FiX />
            </button>
          )}
        </div>

        {searchTerm && (
          <div className="search-results-info">
            {filteredProducts.length} resultado{filteredProducts.length !== 1 ? 's' : ''} 
            {filteredProducts.length > 0 && ` · ${availableCount} disponible${availableCount !== 1 ? 's' : ''}`}
          </div>
        )}
      </div>

      {/* Grid de productos */}
      <main className="products-section">
        {filteredProducts.length === 0 ? (
          <div className="no-results">
            <div className="no-results-icon">∅</div>
            <h2 className="no-results-title">Sin resultados</h2>
            <p className="no-results-text">
              No encontramos productos que coincidan con "{searchTerm}"
            </p>
            <button className="no-results-button" onClick={clearSearch}>
              Ver todos los productos
            </button>
          </div>
        ) : (
          <div className="products-grid">
            {filteredProducts.map((product, index) => (
              <ProductCard
                key={product.id}
                product={product}
                onAddToCart={handleAddToCart}
                index={index}
              />
            ))}
          </div>
        )}
      </main>

      {/* Footer minimalista */}
      <footer className="store-footer">
        <div className="footer-content">
          <p>© 2026 SneakerZone · Cuenca, Ecuador</p>
          <div className="footer-links">
            <a href="#terms">Términos</a>
            <span>·</span>
            <a href="#privacy">Privacidad</a>
            <span>·</span>
            <a href="#contact">Contacto</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Store;