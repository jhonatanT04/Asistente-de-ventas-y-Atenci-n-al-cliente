# 📸 Directorio de Imágenes de Productos

Este directorio contiene las imágenes de los productos que se mostrarán en la tienda.

## 📋 Cómo Agregar Imágenes

### Opción 1: Descargar Imágenes Manualmente

Descarga las imágenes de los productos y guárdalas con el **nombre del código de barras**:

```
public/images/products/
├── 7501234567890.jpg    (Nike Pegasus 40)
├── 7501234567891.jpg    (Nike Air Max 90)
├── 7501234567894.jpg    (Nike Court Vision Low)
├── 7501234567895.jpg    (Nike Air Force 1)
├── 8806098934474.jpg    (Adidas Ultraboost)
├── 8806098934475.jpg    (Adidas Supernova 3)
├── 8806098934478.jpg    (Adidas Samba OG)
└── ...
```

### Opción 2: Usar URLs Externas (Sin descargar)

Si prefieres usar imágenes externas, las imágenes ya están configuradas con URLs de fallback en `src/utils/productImages.ts`.

Las URLs de fallback se usarán automáticamente si no existe la imagen local.

---

## 🔍 Dónde Encontrar Imágenes

### Nike Products
- Sitio oficial: https://www.nike.com/
- Busca el producto por nombre
- Click derecho en la imagen → "Guardar imagen como..."
- Renombra con el código de barras (ej: `7501234567891.jpg`)

### Adidas Products
- Sitio oficial: https://www.adidas.com/
- Mismo proceso que Nike

### Puma Products
- Sitio oficial: https://www.puma.com/

### New Balance Products
- Sitio oficial: https://www.newbalance.com/

---

## 📝 Lista Completa de Productos

| Código Barras | Producto | Imagen Sugerida |
|---------------|----------|-----------------|
| 7501234567890 | Nike Air Zoom Pegasus 40 | [Nike.com](https://www.nike.com/t/pegasus-40) |
| 7501234567891 | Nike Air Max 90 | [Nike.com](https://www.nike.com/t/air-max-90) |
| 7501234567892 | Nike React Infinity Run 4 | [Nike.com](https://www.nike.com/) |
| 7501234567893 | Nike ZoomX Vaporfly 3 | [Nike.com](https://www.nike.com/) |
| 7501234567894 | Nike Court Vision Low | [Nike.com](https://www.nike.com/) |
| 7501234567895 | Nike Air Force 1 '07 | [Nike.com](https://www.nike.com/t/air-force-1) |
| 7501234567896 | Nike Revolution 7 | [Nike.com](https://www.nike.com/) |
| 7501234567897 | Nike Downshifter 12 | [Nike.com](https://www.nike.com/) |
| 7501234567898 | Nike Blazer Mid '77 | [Nike.com](https://www.nike.com/) |
| 7501234567899 | Nike Metcon 9 | [Nike.com](https://www.nike.com/) |
| 8806098934474 | Adidas Ultraboost Light | [Adidas.com](https://www.adidas.com/) |
| 8806098934475 | Adidas Supernova 3 | [Adidas.com](https://www.adidas.com/) |
| 8806098934476 | Adidas Duramo SL | [Adidas.com](https://www.adidas.com/) |
| 8806098934477 | Adidas Stan Smith | [Adidas.com](https://www.adidas.com/stan-smith) |
| 8806098934478 | Adidas Samba OG | [Adidas.com](https://www.adidas.com/samba) |
| 8806098934479 | Adidas Forum Low | [Adidas.com](https://www.adidas.com/) |
| 8806098934480 | Adidas Gazelle | [Adidas.com](https://www.adidas.com/gazelle) |
| 8806098934481 | Adidas Terrex Swift R3 GTX | [Adidas.com](https://www.adidas.com/) |
| 4063697234567 | Puma Velocity Nitro 2 | [Puma.com](https://www.puma.com/) |
| 4063697234568 | Puma Deviate Nitro Elite 2 | [Puma.com](https://www.puma.com/) |
| 4063697234569 | Puma Suede Classic XXI | [Puma.com](https://www.puma.com/) |
| 4063697234570 | Puma RS-X Efekt | [Puma.com](https://www.puma.com/) |
| 4063697234571 | Puma Caven 2.0 | [Puma.com](https://www.puma.com/) |
| 4063697234572 | Puma Clyde All-Pro | [Puma.com](https://www.puma.com/) |
| 0195173234567 | New Balance Fresh Foam X 1080v13 | [NewBalance.com](https://www.newbalance.com/) |
| 0195173234568 | New Balance FuelCell SuperComp Elite v4 | [NewBalance.com](https://www.newbalance.com/) |
| 0195173234569 | New Balance 574 Core | [NewBalance.com](https://www.newbalance.com/574) |
| 0195173234570 | New Balance 327 | [NewBalance.com](https://www.newbalance.com/327) |
| 8884071234567 | Calcetines Nike Crew Performance | [Nike.com](https://www.nike.com/) |
| 0885580234567 | Plantillas Dr. Scholl's | [Amazon](https://www.amazon.com/) |
| 5060101234567 | Spray Crep Protect | [Amazon](https://www.amazon.com/) |
| 1234567890123 | Cordones Premium | [Amazon](https://www.amazon.com/) |

---

## ⚙️ Formato Recomendado

- **Formato:** JPG o PNG
- **Tamaño:** Mínimo 400x300px (recomendado: 800x600px o 1200x900px)
- **Ratio:** 4:3 (horizontal)
- **Peso:** Máximo 500KB por imagen (optimiza con TinyPNG si es necesario)

---

## 🔄 Fallback Automático

Si no agregas imágenes aquí, el sistema usará automáticamente:
1. **Primero:** Intenta cargar la imagen local desde esta carpeta
2. **Si falla:** Usa la URL de fallback configurada (sitio oficial)
3. **Si también falla:** Muestra un placeholder con ícono de paquete

---

## 🧪 Verificar

Para verificar que las imágenes funcionan:
1. Guarda la imagen con el nombre del barcode (ej: `7501234567891.jpg`)
2. Reinicia el servidor React: `npm start`
3. Ve a `/tienda` y verifica que aparezca la imagen

Si no aparece, revisa:
- El nombre del archivo coincide exactamente con el código de barras
- La extensión es `.jpg` (minúsculas)
- El archivo está en la carpeta correcta
