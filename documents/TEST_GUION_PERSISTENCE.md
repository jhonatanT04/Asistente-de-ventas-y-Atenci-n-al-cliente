# Test de Persistencia del Flujo de Guion

## Implementación Completada

### Backend
- ChatHistoryService creado y registrado en container.py
- Metadata con `siguiente_paso` y `mejor_opcion_id` se guarda en procesarGuionAgente2
- Metadata se guarda también en continuarConversacion
- Mensajes completos (con formato de productos) se persisten en PostgreSQL
- Session reconstruction desde PostgreSQL cuando Redis expira

### Frontend
- getChatHistory implementado en graphqlservices.ts
- loadChatHistory carga mensajes al montar componente
- guionFlow state se restaura desde metadata del último mensaje AGENT
- handleSendMessage verifica guionFlow.active antes de decidir flujo
- Iconos cambiados a emojis (📄 🔄 ✖️)
- Chat window aumentado (550x750px)

---

## Plan de Pruebas

### Test 1: Flujo Completo Sin Recargar
**Objetivo**: Verificar que el flujo de guion funciona normalmente

1. Abrir chatbot
2. Enviar: `"quiero las air max y las air force"`
3. **Esperar respuesta** con comparación de productos
4. **Verificar**: Debe mostrar 2+ productos con precios, scores, razones
5. **Verificar**: Último mensaje debe terminar con "¿Te interesa este producto? Responde **"sí"** o **"no"**."
6. Responder: `"sí"`
7. **Esperar respuesta**
8. **Verificar**: Debe pedir datos de envío (talla + dirección)

**Estado esperado**: Flujo completo funciona

---

### Test 2: Persistencia Básica (Recargar Después de Guion)
**Objetivo**: Verificar que el historial se carga después de recargar

1. Continuar desde Test 1 (después de recibir comparación de productos)
2. **RECARGAR PÁGINA** (F5)
3. **Verificar**: Deben aparecer todos los mensajes anteriores
4. **Verificar**: El mensaje de comparación debe mostrar productos completos con formato
5. **Verificar**: No debe aparecer mensaje de bienvenida
6. Abrir consola del navegador (F12)
7. **Buscar log**: ` Flujo de guion restaurado:"`
8. **Verificar**: Debe mostrar `mejorOpcionId` y `siguientePaso`

**Estado esperado**: Historial cargado, guionFlow restaurado

---

### Test 3: Continuar Flujo Después de Recargar (PRUEBA CRÍTICA)
**Objetivo**: Verificar que responder "sí" después de recargar continúa el flujo

1. Continuar desde Test 2 (después de recargar)
2. Responder: `"sí"`
3. Abrir consola del navegador (F12)
4. **Verificar log**: Debe aparecer `" Continuando conversación de guion: sí"`
5. **Verificar log**: Debe aparecer `" Enviando mutation continuarConversacion..."`
6. **NO debe aparecer**: `"Llamando semanticSearch con query: sí"` (esto sería Alex, no guion)
7. **Esperar respuesta**
8. **Verificar**: Debe pedir talla + dirección (NO respuesta genérica de Alex)
9. **Verificar**: El mensaje debe ser específico al producto seleccionado

**Estado esperado**: Flujo de guion continúa correctamente después de recargar

---

### Test 4: Flujo Completo de Orden con Recarga
**Objetivo**: Verificar persistencia en múltiples etapas

1. Enviar: `"quiero las pegasus"`
2. **Esperar respuesta** con comparación
3. **RECARGAR PÁGINA** (F5)
4. Responder: `"sí"`
5. **Esperar respuesta** pidiendo datos de envío
6. **RECARGAR PÁGINA** (F5)
7. Responder: `"talla 42, calle falsa 123"`
8. **Esperar respuesta**
9. **Verificar**: Debe crear orden y mostrar número de orden
10. **Verificar**: `siguiente_paso` debe ser `"orden_completada"`
11. **RECARGAR PÁGINA** (F5)
12. Responder cualquier cosa
13. **Verificar**: NO debe continuar flujo de guion (porque ya terminó)

**Estado esperado**: Orden creada, flujo terminado correctamente

---

### Test 5: Rechazo y Alternativa
**Objetivo**: Verificar que el rechazo funciona con persistencia

1. Enviar: `"quiero las ultraboost y las supernova"`
2. **Esperar respuesta** con comparación
3. **RECARGAR PÁGINA** (F5)
4. Responder: `"no"`
5. **Esperar respuesta**
6. **Verificar**: Debe ofrecer producto alternativo
7. **Verificar**: Debe actualizar `mejor_opcion_id` en metadata
8. **RECARGAR PÁGINA** (F5)
9. Responder: `"sí"` (al alternativo)
10. **Verificar**: Debe continuar con el nuevo producto

**Estado esperado**: Alternativas funcionan con persistencia

---

### Test 6: Desconexión WiFi
**Objetivo**: Verificar que mensajes persisten sin conexión

1. Enviar: `"quiero las samba"`
2. **Esperar respuesta**
3. **DESACTIVAR WIFI**
4. **Cerrar navegador completamente**
5. **Reactivar WIFI**
6. **Abrir navegador y chatbot**
7. **Verificar**: Conversación anterior debe aparecer
8. **Verificar**: guionFlow debe estar activo
9. Responder: `"sí"`
10. **Verificar**: Debe continuar flujo correctamente

**Estado esperado**: Persistencia sobrevive desconexión

---

### Test 7: Sesión Redis Expirada
**Objetivo**: Verificar reconstrucción desde PostgreSQL

1. Enviar: `"quiero las vaporfly"`
2. **Esperar respuesta**
3. Conectarse al backend y ejecutar:
   ```bash
   docker exec -it <redis-container> redis-cli
   KEYS session-*
   DEL <session-key>
   ```
4. **RECARGAR PÁGINA** (F5)
5. Responder: `"sí"`
6. Revisar logs del backend
7. **Verificar log**: ` Sesión reconstruida desde PostgreSQL"`
8. **Verificar**: Flujo debe continuar correctamente

**Estado esperado**: Reconstrucción automática funciona

---

### Test 8: Múltiples Conversaciones (Session ID)
**Objetivo**: Verificar que cada conversación tiene su propio historial

1. Enviar: `"quiero las air max"`
2. **Esperar respuesta**
3. Click en botón "🔄" (Nueva conversación)
4. **Verificar**: Mensajes anteriores deben desaparecer
5. **Verificar**: Debe aparecer mensaje de bienvenida
6. **Verificar localStorage**: `chat_session_id` debe cambiar
7. Enviar: `"hola"`
8. **RECARGAR PÁGINA** (F5)
9. **Verificar**: Solo debe aparecer "hola" y respuesta (no la conversación anterior)

**Estado esperado**: Sesiones aisladas correctamente

---

## Logs a Buscar en Consola

### Frontend (F12 → Console)
``` Historial cargado: N mensajes Flujo de guion restaurado: { mejorOpcionId: "...", siguientePaso: "confirmar_compra" }
Continuando conversación de guion: sí
Enviando mutation continuarConversacion...
Resultado completo: { ... }
```

### Backend (Terminal)
```
Mensaje creado: <uuid> (sesión=session-..., rol=AGENT) FLUJO COMPLETADO EXITOSAMENTE
   • Siguiente paso: confirmar_compra
   • Mensaje generado para usuario (800+ caracteres)
Historial recuperado: N mensajes de sesión session-... Sesión reconstruida desde PostgreSQL: session-...
```

---

## Errores Comunes y Soluciones

### Error 1: "Historial cargado: 0 mensajes"
**Causa**: No hay token de autenticación o backend no guardó mensajes
**Solución**:
- Verificar que `localStorage.getItem('access_token')` existe
- Revisar logs del backend para ver si hay errores en `add_message`

### Error 2: "guionFlow NO se restaura" (active = false)
**Causa**: Metadata no tiene `mejor_opcion_id` o `siguiente_paso`
**Solución**:
- Verificar que backend guardó metadata correctamente en procesarGuionAgente2
- Revisar línea 568-572 de mutations.py
- Verificar que `siguiente_paso` no es 'nueva_conversacion' o 'orden_completada'

### Error 3: "Responde como Alex después de recargar"
**Causa**: guionFlow.active es false, cae en semanticSearch
**Solución**:
- Verificar que metadata del último mensaje AGENT tiene los campos correctos
- Revisar que JSON.parse no falla (añadir log en línea 177 de chatbot.tsx)
- Verificar que `siguientePaso !== 'nueva_conversacion'`

### Error 4: "Mensaje truncado después de recargar"
**Causa**: Backend guarda solo parte del mensaje
**Solución**:
- Verificar que líneas 521-543 de mutations.py construyen mensaje completo
- NO solo guardar `mensaje` del LLM, construir con productos formateados

---

## Checklist de Verificación

- [ ] Test 1: Flujo normal sin recargar
- [ ] Test 2: Historial se carga después de recargar
- [ ] Test 3: **Responder "sí" después de recargar continúa guion** (CRÍTICO)
- [ ] Test 4: Flujo completo con múltiples recargas
- [ ] Test 5: Rechazo y alternativas con persistencia
- [ ] Test 6: Desconexión WiFi
- [ ] Test 7: Redis expira, reconstruye desde PostgreSQL
- [ ] Test 8: Múltiples conversaciones aisladas

---

## Resultado Esperado

Al completar todos los tests, el sistema debe:
1. Persistir todos los mensajes en PostgreSQL
2. Cargar historial al recargar página
3. Restaurar estado `guionFlow` desde metadata
4. Continuar flujo correctamente después de recargar
5. Reconstruir sesión desde PostgreSQL si Redis expira
6. Mantener conversaciones aisladas por session_id

**El requisito del ingeniero está cumplido**: "No se pierde el contexto de la conversación, conversaciones pendientes"
