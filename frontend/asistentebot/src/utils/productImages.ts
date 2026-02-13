/**
 * Mapeo de códigos de barras a URLs de imágenes de productos.
 *
 * IMPORTANTE: Las imágenes se buscan primero en /images/products/ (local)
 * Si no existe localmente, usa la URL de fallback (Lorem Picsum)
 *
 * Para usar imágenes locales:
 * 1. Descarga las imágenes de los productos
 * 2. Guárdalas en: public/images/products/{barcode}.jpg
 * 3. Ejemplo: public/images/products/7501234567891.jpg
 */

export interface ProductImage {
  barcode: string;
  localPath: string;      // Ruta en public/images/products/
  fallbackUrl?: string;    // URL externa si no existe local
  productName: string;     // Nombre del producto (para referencia)
}

export const PRODUCT_IMAGES: Record<string, ProductImage> = {
  // ============================================
  // NIKE - RUNNING
  // ============================================
  '7501234567890': {
    barcode: '7501234567890',
    localPath: '/images/products/7501234567890.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/7c5f3d33-a5d7-42e8-b9e0-2e0e8c634e1a/pegasus-40-zapatillas-de-running-carretera-hombre.jpg',
    productName: 'Nike Air Zoom Pegasus 40'
  },
  '7501234567892': {
    barcode: '7501234567892',
    localPath: '/images/products/7501234567892.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/c2d3f68e-76f4-4f54-b8b1-7a1e8d0c4b4e/react-infinity-run-4-zapatillas-de-running.jpg',
    productName: 'Nike React Infinity Run 4'
  },
  '7501234567893': {
    barcode: '7501234567893',
    localPath: '/images/products/7501234567893.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/3d3c3d33-a5d7-42e8-b9e0-2e0e8c634e1a/vaporfly-3-zapatillas-de-competicion.jpg',
    productName: 'Nike ZoomX Vaporfly 3'
  },
  '7501234567896': {
    barcode: '7501234567896',
    localPath: '/images/products/7501234567896.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/revolution-7-zapatillas-de-running.jpg',
    productName: 'Nike Revolution 7'
  },
  '7501234567897': {
    barcode: '7501234567897',
    localPath: '/images/products/7501234567897.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/downshifter-12-zapatillas-de-running.jpg',
    productName: 'Nike Downshifter 12'
  },

  // ============================================
  // NIKE - LIFESTYLE
  // ============================================
  '7501234567891': {
    barcode: '7501234567891',
    localPath: '/images/products/7501234567891.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/23d5b499-0cbe-41c2-85a5-c7e5e0f8e5a5/air-max-90-zapatillas.jpg',
    productName: 'Nike Air Max 90'
  },
  '7501234567894': {
    barcode: '7501234567894',
    localPath: '/images/products/7501234567894.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/court-vision-low-zapatillas.jpg',
    productName: 'Nike Court Vision Low'
  },
  '7501234567895': {
    barcode: '7501234567895',
    localPath: '/images/products/7501234567895.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/b7d9211c-26e7-431a-ac24-b0540fb3c00f/air-force-1-07-zapatillas.jpg',
    productName: 'Nike Air Force 1 \'07'
  },
  '7501234567898': {
    barcode: '7501234567898',
    localPath: '/images/products/7501234567898.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/blazer-mid-77-vintage-zapatillas.jpg',
    productName: 'Nike Blazer Mid \'77'
  },

  // ============================================
  // NIKE - TRAINING
  // ============================================
  '7501234567899': {
    barcode: '7501234567899',
    localPath: '/images/products/7501234567899.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/metcon-9-zapatillas-de-entrenamiento.jpg',
    productName: 'Nike Metcon 9'
  },

  // ============================================
  // ADIDAS - RUNNING
  // ============================================
  '8806098934474': {
    barcode: '8806098934474',
    localPath: '/images/products/8806098934474.jpg',
    fallbackUrl: 'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/ultraboost-light-running-shoes.jpg',
    productName: 'Adidas Ultraboost Light'
  },
  '8806098934475': {
    barcode: '8806098934475',
    localPath: '/images/products/8806098934475.jpg',
    fallbackUrl: 'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/supernova-3-running-shoes.jpg',
    productName: 'Adidas Supernova 3'
  },
  '8806098934476': {
    barcode: '8806098934476',
    localPath: '/images/products/8806098934476.jpg',
    fallbackUrl: 'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/duramo-sl-running-shoes.jpg',
    productName: 'Adidas Duramo SL'
  },

  // ============================================
  // ADIDAS - LIFESTYLE
  // ============================================
  '8806098934477': {
    barcode: '8806098934477',
    localPath: '/images/products/8806098934477.jpg',
    fallbackUrl: 'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/stan-smith-shoes.jpg',
    productName: 'Adidas Stan Smith'
  },
  '8806098934478': {
    barcode: '8806098934478',
    localPath: '/images/products/8806098934478.jpg',
    fallbackUrl: 'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/samba-og-shoes.jpg',
    productName: 'Adidas Samba OG'
  },
  '8806098934479': {
    barcode: '8806098934479',
    localPath: '/images/products/8806098934479.jpg',
    fallbackUrl: 'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/forum-low-shoes.jpg',
    productName: 'Adidas Forum Low'
  },
  '8806098934480': {
    barcode: '8806098934480',
    localPath: '/images/products/8806098934480.jpg',
    fallbackUrl: 'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/gazelle-shoes.jpg',
    productName: 'Adidas Gazelle'
  },

  // ============================================
  // ADIDAS - OUTDOOR
  // ============================================
  '8806098934481': {
    barcode: '8806098934481',
    localPath: '/images/products/8806098934481.jpg',
    fallbackUrl: 'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/terrex-swift-r3-gtx-hiking-shoes.jpg',
    productName: 'Adidas Terrex Swift R3 GTX'
  },

  // ============================================
  // PUMA - RUNNING
  // ============================================
  '4063697234567': {
    barcode: '4063697234567',
    localPath: '/images/products/4063697234567.jpg',
    fallbackUrl: 'https://images.puma.com/image/upload/f_auto,q_auto,b_rgb:fafafa/velocity-nitro-2-running-shoes.jpg',
    productName: 'Puma Velocity Nitro 2'
  },
  '4063697234568': {
    barcode: '4063697234568',
    localPath: '/images/products/4063697234568.jpg',
    fallbackUrl: 'https://images.puma.com/image/upload/f_auto,q_auto,b_rgb:fafafa/deviate-nitro-elite-2-running-shoes.jpg',
    productName: 'Puma Deviate Nitro Elite 2'
  },

  // ============================================
  // PUMA - LIFESTYLE
  // ============================================
  '4063697234569': {
    barcode: '4063697234569',
    localPath: '/images/products/4063697234569.jpg',
    fallbackUrl: 'https://images.puma.com/image/upload/f_auto,q_auto,b_rgb:fafafa/suede-classic-xxi-sneakers.jpg',
    productName: 'Puma Suede Classic XXI'
  },
  '4063697234570': {
    barcode: '4063697234570',
    localPath: '/images/products/4063697234570.jpg',
    fallbackUrl: 'https://images.puma.com/image/upload/f_auto,q_auto,b_rgb:fafafa/rs-x-efekt-sneakers.jpg',
    productName: 'Puma RS-X Efekt'
  },
  '4063697234571': {
    barcode: '4063697234571',
    localPath: '/images/products/4063697234571.jpg',
    fallbackUrl: 'https://images.puma.com/image/upload/f_auto,q_auto,b_rgb:fafafa/caven-2-sneakers.jpg',
    productName: 'Puma Caven 2.0'
  },

  // ============================================
  // PUMA - BASKETBALL
  // ============================================
  '4063697234572': {
    barcode: '4063697234572',
    localPath: '/images/products/4063697234572.jpg',
    fallbackUrl: 'https://images.puma.com/image/upload/f_auto,q_auto,b_rgb:fafafa/clyde-all-pro-basketball-shoes.jpg',
    productName: 'Puma Clyde All-Pro'
  },

  // ============================================
  // NEW BALANCE - RUNNING
  // ============================================
  '0195173234567': {
    barcode: '0195173234567',
    localPath: '/images/products/0195173234567.jpg',
    fallbackUrl: 'https://nb.scene7.com/is/image/NB/fresh-foam-x-1080v13-running-shoes.jpg',
    productName: 'New Balance Fresh Foam X 1080v13'
  },
  '0195173234568': {
    barcode: '0195173234568',
    localPath: '/images/products/0195173234568.jpg',
    fallbackUrl: 'https://nb.scene7.com/is/image/NB/fuelcell-supercomp-elite-v4-running-shoes.jpg',
    productName: 'New Balance FuelCell SuperComp Elite v4'
  },

  // ============================================
  // NEW BALANCE - LIFESTYLE
  // ============================================
  '0195173234569': {
    barcode: '0195173234569',
    localPath: '/images/products/0195173234569.jpg',
    fallbackUrl: 'https://nb.scene7.com/is/image/NB/574-core-sneakers.jpg',
    productName: 'New Balance 574 Core'
  },
  '0195173234570': {
    barcode: '0195173234570',
    localPath: '/images/products/0195173234570.jpg',
    fallbackUrl: 'https://nb.scene7.com/is/image/NB/327-sneakers.jpg',
    productName: 'New Balance 327'
  },

  // ============================================
  // ACCESORIOS
  // ============================================
  '8884071234567': {
    barcode: '8884071234567',
    localPath: '/images/products/8884071234567.jpg',
    fallbackUrl: 'https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/calcetines-crew-performance.jpg',
    productName: 'Calcetines Nike Crew Performance (Pack x3)'
  },
  '0885580234567': {
    barcode: '0885580234567',
    localPath: '/images/products/0885580234567.jpg',
    fallbackUrl: 'https://m.media-amazon.com/images/I/dr-scholls-insoles.jpg',
    productName: 'Plantillas Ortopédicas Dr. Scholl\'s'
  },
  '5060101234567': {
    barcode: '5060101234567',
    localPath: '/images/products/5060101234567.jpg',
    fallbackUrl: 'https://m.media-amazon.com/images/I/crep-protect-spray.jpg',
    productName: 'Spray Impermeabilizante Crep Protect'
  },
  '1234567890123': {
    barcode: '1234567890123',
    localPath: '/images/products/1234567890123.jpg',
    fallbackUrl: 'https://m.media-amazon.com/images/I/shoelaces-premium.jpg',
    productName: 'Cordones de Repuesto Premium'
  }
};

/**
 * Obtiene la URL de imagen para un producto dado su código de barras.
 * Primero intenta usar la imagen local, si no existe usa el fallback.
 *
 * @param barcode - Código de barras del producto
 * @param productId - ID del producto (para fallback de Lorem Picsum)
 * @returns URL de la imagen
 */
export const getProductImageUrl = (barcode: string | null | undefined, productId: string): string => {
  // Si no hay barcode, usar placeholder de Lorem Picsum
  if (!barcode || !PRODUCT_IMAGES[barcode]) {
    return `https://picsum.photos/seed/${productId}/400/300`;
  }

  const imageData = PRODUCT_IMAGES[barcode];

  // Retornar la ruta local (si existe) o el fallback
  // El navegador intentará cargar desde public/ automáticamente
  return imageData.localPath;
};

/**
 * Obtiene la URL de fallback (externa) para un código de barras.
 * Útil si quieres forzar el uso de la imagen externa.
 */
export const getFallbackImageUrl = (barcode: string): string | undefined => {
  return PRODUCT_IMAGES[barcode]?.fallbackUrl;
};

/**
 * Verifica si existe una imagen configurada para un código de barras.
 */
export const hasProductImage = (barcode: string | null | undefined): boolean => {
  if (!barcode) return false;
  return barcode in PRODUCT_IMAGES;
};

/**
 * Lista de todos los códigos de barras con imágenes configuradas.
 * Útil para debugging o para verificar qué productos tienen imagen.
 */
export const getAllProductBarcodes = (): string[] => {
  return Object.keys(PRODUCT_IMAGES);
};
