# Guía de Despliegue en Google Cloud Platform

Esta guía contiene todos los comandos necesarios para gestionar el despliegue de la aplicación en GCP.

---

## Información del Despliegue

### Detalles de la VM
- **Nombre**: `sales-ai-app`
- **Zona**: `us-central1-a`
- **Tipo de máquina**: `e2-small` (2 vCPU, 2 GB RAM)
- **IP Pública**: `34.44.205.241`
- **Sistema Operativo**: Ubuntu 22.04 LTS

### URLs de Acceso
- **Frontend**: http://34.44.205.241:3000
- **Backend API**: http://34.44.205.241:8000
- **GraphQL Playground**: http://34.44.205.241:8000/graphql
- **API Docs**: http://34.44.205.241:8000/docs

### Servicios Desplegados
- **PostgreSQL** (puerto 5432) - Base de datos con extensión pgvector
- **Redis** (puerto 6379) - Caché y sesiones
- **Backend** (puerto 8000) - FastAPI + Vertex AI (Gemini)
- **Frontend** (puerto 3000) - React 18 + Nginx

---

## Conexión a la VM

### Conectarse via SSH
```bash
gcloud compute ssh sales-ai-app --zone=us-central1-a
```

### Configurar Proyecto GCP (si es necesario)
```bash
gcloud config set project arch-dev-agent
```

### Conectarse sin autenticación interactiva
```bash
gcloud compute ssh sales-ai-app --zone=us-central1-a --quiet
```

---

## Gestión de Contenedores Docker

### Ver Estado de Todos los Servicios
```bash
cd ~/app
sudo docker-compose ps
```

### Ver Todos los Contenedores (incluyendo detenidos)
```bash
sudo docker ps -a
```

---

## Reinicio de Servicios

### Reiniciar Todos los Servicios
```bash
cd ~/app
sudo docker-compose restart
```

### Reiniciar Solo el Backend
```bash
cd ~/app
sudo docker-compose restart backend
```

### Reiniciar Solo el Frontend
```bash
cd ~/app
sudo docker-compose restart frontend
```

### Reiniciar PostgreSQL
```bash
cd ~/app
sudo docker-compose restart postgres
```

### Reiniciar Redis
```bash
cd ~/app
sudo docker-compose restart redis
```

---

## Visualización de Logs

### Logs del Backend (IMPORTANTE)

#### Ver logs en tiempo real
```bash
cd ~/app
sudo docker-compose logs -f backend
```

#### Ver últimas 50 líneas
```bash
cd ~/app
sudo docker-compose logs --tail=50 backend
```

#### Ver logs con timestamps
```bash
cd ~/app
sudo docker-compose logs -f -t backend
```

#### Filtrar logs de errores
```bash
cd ~/app
sudo docker-compose logs backend 2>&1 | grep -i "error"
```

#### Filtrar logs de Vertex AI / Gemini
```bash
cd ~/app
sudo docker-compose logs backend 2>&1 | grep -i "gemini\|vertex"
```

#### Filtrar logs de CORS
```bash
cd ~/app
sudo docker-compose logs backend 2>&1 | grep -i "cors"
```

### Logs del Frontend
```bash
cd ~/app
sudo docker-compose logs -f frontend
```

### Logs de PostgreSQL
```bash
cd ~/app
sudo docker-compose logs -f postgres
```

### Logs de Todos los Servicios
```bash
cd ~/app
sudo docker-compose logs -f
```

### Logs de Todos los Servicios (últimas 100 líneas)
```bash
cd ~/app
sudo docker-compose logs --tail=100
```

---

## Detener y Levantar Servicios

### Detener Todos los Servicios
```bash
cd ~/app
sudo docker-compose down
```

### Detener sin eliminar volúmenes
```bash
cd ~/app
sudo docker-compose stop
```

### Levantar Todos los Servicios
```bash
cd ~/app
export $(cat .env.production | grep -v '^#' | xargs)
sudo -E docker-compose up -d
```

### Levantar con rebuild (si hay cambios en el código)
```bash
cd ~/app
export $(cat .env.production | grep -v '^#' | xargs)
sudo -E docker-compose up -d --build
```

---

## Debugging y Troubleshooting

### Entrar al Contenedor del Backend
```bash
sudo docker exec -it app_backend_1 bash
```

### Entrar al Contenedor del Frontend
```bash
sudo docker exec -it app_frontend_1 sh
```

### Ver Variables de Entorno del Backend
```bash
sudo docker exec app_backend_1 env
```

### Verificar Archivo .env del Backend
```bash
sudo docker exec app_backend_1 cat /app/.env
```

### Verificar Credenciales de Google Cloud
```bash
sudo docker exec app_backend_1 ls -la /app/credentials/
sudo docker exec app_backend_1 cat /app/credentials/google-credentials.json | head -5
```

### Verificar Conexión a PostgreSQL
```bash
sudo docker exec app_postgres_1 psql -U postgres -d app_db -c "\dt"
```

### Ver Usuarios en la Base de Datos
```bash
sudo docker exec app_postgres_1 psql -U postgres -d app_db -c "SELECT username, email, role FROM users;"
```

### Ver Productos en la Base de Datos
```bash
sudo docker exec app_postgres_1 psql -U postgres -d app_db -c "SELECT COUNT(*) FROM products;"
```

### Test de Health Check del Backend
```bash
curl http://localhost:8000/health
```

### Test de Login desde la VM
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

---

## Actualización de Código

### 1. Preparar Nueva Versión Localmente
```bash
# En tu máquina local
cd "/home/felipep/Documentos/universidad/universidad 7mo/aprendizaje automatico/practica 4"

# Comprimir proyecto
tar --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    -czf sales-ai-app-update.tar.gz .
```

### 2. Copiar a la VM
```bash
gcloud compute scp sales-ai-app-update.tar.gz sales-ai-app:~ --zone=us-central1-a
```

### 3. Desplegar en la VM
```bash
# Conectarse a la VM
gcloud compute ssh sales-ai-app --zone=us-central1-a

# Backup del código actual
cd ~
cp -r app app_backup_$(date +%Y%m%d_%H%M%S)

# Descomprimir nueva versión
tar -xzf sales-ai-app-update.tar.gz -C ~/app

# Rebuild y reiniciar
cd ~/app
export $(cat .env.production | grep -v '^#' | xargs)
sudo docker-compose down
sudo -E docker-compose build
sudo -E docker-compose up -d

# Verificar logs
sudo docker-compose logs -f backend
```

---

## Gestión de Base de Datos

### Backup de la Base de Datos
```bash
sudo docker exec app_postgres_1 pg_dump -U postgres app_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restaurar Base de Datos
```bash
cat backup_YYYYMMDD_HHMMSS.sql | sudo docker exec -i app_postgres_1 psql -U postgres app_db
```

### Reinicializar Base de Datos (CUIDADO: Borra todos los datos)
```bash
cd ~/app
sudo docker-compose exec backend python init_db.py
sudo docker-compose exec backend python init_db_2.py
```

---

## Monitoreo

### Ver Uso de Recursos
```bash
# CPU y memoria de contenedores
sudo docker stats

# Espacio en disco
df -h

# Memoria de la VM
free -h
```

### Ver Logs del Sistema
```bash
sudo journalctl -u docker -f
```

---

## Seguridad

### Ver Reglas de Firewall
```bash
gcloud compute firewall-rules list
```

### Ver IP Pública de la VM
```bash
gcloud compute instances describe sales-ai-app \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

---

## Comandos de Emergencia

### Reinicio Completo (si nada funciona)
```bash
cd ~/app
sudo docker-compose down
sudo docker system prune -f
export $(cat .env.production | grep -v '^#' | xargs)
sudo -E docker-compose up -d --build
```

### Reiniciar la VM Completa
```bash
gcloud compute instances reset sales-ai-app --zone=us-central1-a
```

### Ver Últimos Errores en el Backend
```bash
cd ~/app
sudo docker-compose logs backend 2>&1 | grep -i "error\|exception" | tail -20
```

---

## Notas Importantes

1. **Siempre cargar variables de entorno** antes de ejecutar `docker-compose`:
   ```bash
   export $(cat .env.production | grep -v '^#' | xargs)
   ```

2. **El archivo `.env` dentro del contenedor backend** a veces se resetea. Si hay errores de conexión, verificar:
   ```bash
   sudo docker exec app_backend_1 cat /app/.env
   ```

3. **Credenciales de Google Cloud** deben estar en:
   ```bash
   ~/app/arch-dev-agent-87f23e12bec3.json
   ```

4. **Frontend requiere rebuild** si cambias `REACT_APP_API_URL`:
   ```bash
   sudo docker-compose build --build-arg REACT_APP_API_URL=http://34.44.205.241:8000 frontend
   sudo docker-compose up -d frontend
   ```
