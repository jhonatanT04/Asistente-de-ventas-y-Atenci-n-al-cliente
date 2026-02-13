#!/bin/bash
# Script para reiniciar la base de datos desde cero
# Incluye: barcodes, descuentos, promociones, categorías, marcas
# Uso: ./reset_database.sh

set -e  # Detenerse en cualquier error

# Exportar SECRET_KEY si no está definida (para evitar error en init.db.py)
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY="super-secret-sales-agent-key-2026-cuenca"
    export JWT_SECRET="super-secret-sales-agent-key-2026-cuenca"
    echo "🔑 Usando SECRET_KEY por defecto"
fi

echo "=============================================="
echo " 🔄 REINICIO COMPLETO DE BASE DE DATOS"
echo "=============================================="
echo ""
echo "Este script reiniciará la BD con:"
echo "  • Códigos de barras (barcodes)"
echo "  • Sistema de descuentos y promociones"
echo "  • Categorías y marcas"
echo "  • Precios originales vs finales"
echo ""
read -p "¿Continuar? (s/N): " confirm
if [[ $confirm != [sS] ]]; then
    echo "❌ Cancelado"
    exit 1
fi

echo ""
echo "🛑 Deteniendo contenedores y eliminando volúmenes..."
docker-compose down -v --remove-orphans

echo "🗑️  Eliminando volumen de datos de PostgreSQL (forzado)..."
docker volume rm -f practica-4_postgres_data 2>/dev/null || true
docker volume rm -f postgres_data 2>/dev/null || true
docker volume rm -f "$(basename "$PWD")_postgres_data" 2>/dev/null || true

echo "🧹 Limpiando contenedores huérfanos..."
docker-compose rm -f 2>/dev/null || true

echo "🚀 Iniciando contenedores limpios..."
docker-compose up -d

echo "⏳ Esperando a que PostgreSQL esté listo..."
sleep 5

# Verificar que PostgreSQL responde
until docker exec sales_agent_db pg_isready -U postgres > /dev/null 2>&1; do
    echo "   PostgreSQL aún no está listo... esperando"
    sleep 2
done

echo "✅ PostgreSQL está listo"

echo "📦 Instalando dependencias con uv..."
uv pip install email-validator slowapi asyncpg --quiet

echo ""
echo "🗃️  Creando tablas y usuarios..."
uv run python init.db.py

echo ""
echo "📚 Cargando catálogo completo de productos..."
uv run python init_db_2.py

echo ""
echo "🧪 Creando base de datos de tests..."
uv run python init_test_db.py

echo ""
echo "=============================================="
echo "✅ BASE DE DATOS REINICIADA EXITOSAMENTE"
echo "=============================================="
echo ""

# Verificación final
echo "📊 Verificando datos..."
docker exec sales_agent_db psql -U postgres -d app_db -c "
SELECT 
    COUNT(*) as total_productos,
    COUNT(barcode) as con_barcode,
    COUNT(*) FILTER (WHERE is_on_sale) as en_oferta
FROM product_stocks;
" 2>/dev/null || echo "   ⚠️  No se pudo verificar (contenedor puede estar reiniciando)"

echo ""
echo "🗃️  Bases de datos creadas:"
echo "  • app_db (principal)"
echo "  • sales_ai_test (para tests)"
echo ""
echo "👤 Usuarios de prueba:"
echo "  • admin / admin123 (Administrador)"
echo "  • Cliente1 / cliente123 (Cliente)"
echo ""
echo "🚀 Para iniciar el servidor:"
echo "  uv run -m backend.main"
echo ""
echo "🔗 GraphQL Playground:"
echo "  http://localhost:8000/graphql"
echo ""
