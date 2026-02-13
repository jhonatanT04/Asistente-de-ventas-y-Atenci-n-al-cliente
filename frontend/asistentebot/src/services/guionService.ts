/**
 * Servicio para integración del módulo de Guion (Agente 2 → Agente 3)
 * Endpoints de GraphQL para procesamiento de guiones y recomendaciones
 * 
 * Flujo:
 * 1. Agente 2 detecta productos (códigos de barras) → procesarGuionAgente2
 * 2. Agente 3 compara y recomienda → continuarConversacion
 * 3. Usuario aprueba/rechaza → continuarConversacion
 * 4. Solicita datos envío → continuarConversacion
 * 5. Redirige a checkout
 */

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const GRAPHQL_ENDPOINT = `${API_BASE}/graphql`;

// tipos para entrada de guion y respuesta de recomendaciones

export interface ProductoEnGuion {
  codigoBarras: string;
  nombreDetectado: string;
  marca?: string;
  categoria?: string;
  prioridad: 'alta' | 'media' | 'baja';
  motivoSeleccion?: string;
}

export interface PreferenciasUsuario {
  estiloComunicacion?: 'cuencano' | 'juvenil' | 'formal' | 'neutral';
  usoPrevisto?: string;
  nivelActividad?: 'alto' | 'medio' | 'bajo';
  tallaPreferida?: string;
  colorPreferido?: string;
  presupuestoMaximo?: number;
  buscaOfertas?: boolean;
  urgencia?: 'alta' | 'media' | 'baja';
  caracteristicasImportantes?: string[];
}

export interface ContextoBusqueda {
  tipoEntrada: 'texto' | 'voz' | 'imagen' | 'mixta';
  productoMencionadoExplicitamente?: boolean;
  necesitaRecomendacion: boolean;
  intencionPrincipal: 'compra_directa' | 'comparar' | 'informacion';
  restriccionesAdicionales?: string[];
}

export interface GuionEntradaInput {
  sessionId: string;
  productos: ProductoEnGuion[];
  preferencias: PreferenciasUsuario;
  contexto: ContextoBusqueda;
  textoOriginalUsuario: string;
  resumenAnalisis: string;
  confianzaProcesamiento: number;
}

export interface ProductComparison {
  id: string;
  productName: string;
  barcode?: string;
  brand?: string;
  category?: string;
  unitCost: number;
  finalPrice: number;
  savingsAmount?: number;
  isOnSale: boolean;
  discountPercent?: number;
  promotionDescription?: string;
  quantityAvailable: number;
  recommendationScore: number;
  reason: string;
}

export interface RecomendacionResponse {
  success: boolean;
  mensaje: string;
  productos: ProductComparison[];
  mejorOpcionId: string;
  reasoning: string;
  siguientePaso: 'confirmar_compra' | 'solicitar_datos_envio' | 'ir_a_checkout' | 'nueva_conversacion';
  audioUrl?: string;
}

export interface ContinuarConversacionResponse {
  success: boolean;
  mensaje: string;
  mejorOpcionId?: string;
  siguientePaso: 'confirmar_compra' | 'solicitar_datos_envio' | 'ir_a_checkout' | 'nueva_conversacion';
  audioUrl?: string;
}

// helper para incluir token de autenticación en headers

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function graphQLFetch<T>(
  query: string,
  variables?: Record<string, any>
): Promise<{ data?: T; errors?: any[] }> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
  };

  const res = await fetch(GRAPHQL_ENDPOINT, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query, variables }),
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  }

  return res.json();
}

// guion service para manejar el flujo de recomendaciones basado 
// en productos detectados por Agente 2 y la interacción con el usuario en Agente 3

export class GuionService {
  private sessionId: string;

  constructor() {
    // Limpiar session_id antiguo de guion (migración)
    if (localStorage.getItem('guion_session_id')) {
      localStorage.removeItem('guion_session_id');
    }

    this.sessionId = this.getOrCreateSessionId();
  }

  /**
   * Genera o recupera session ID único para el flujo de guion.
   * IMPORTANTE: Usa el mismo session_id que chatService para unificar historial.
   */
  private getOrCreateSessionId(): string {
    // Usar el mismo session_id que chatService
    let sessionId = localStorage.getItem('chat_session_id');
    if (!sessionId) {
      sessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      localStorage.setItem('chat_session_id', sessionId);
    }
    return sessionId;
  }

  /**
   * Resetea la sesión actual (útil para nueva conversación)
   */
  resetSession(): void {
    // Resetear el mismo session_id que chatService
    localStorage.removeItem('chat_session_id');
    this.sessionId = this.getOrCreateSessionId();
  }

  getSessionId(): string {
    return this.sessionId;
  }

  /**
   * 1. PROCESAR GUION AGENTE 2
   * Inicia el flujo procesando productos detectados por Agente 2
   * 
   * @param guion - Datos del guion con productos, preferencias y contexto
   * @returns Recomendación con productos comparados y siguiente paso
   */
  async procesarGuionAgente2(guion: GuionEntradaInput): Promise<RecomendacionResponse | null> {
    const mutation = `
      mutation ProcesarGuion($guion: GuionEntradaInput!) {
        procesarGuionAgente2(guion: $guion) {
          success
          mensaje
          productos {
            id
            productName
            barcode
            brand
            category
            unitCost
            finalPrice
            savingsAmount
            isOnSale
            discountPercent
            promotionDescription
            quantityAvailable
            recommendationScore
            reason
          }
          mejorOpcionId
          reasoning
          siguientePaso
          audioUrl
        }
      }
    `;

    try {
      const result = await graphQLFetch<{ procesarGuionAgente2: RecomendacionResponse }>(
        mutation,
        { guion }
      );

      if (result.errors) {
        console.error(' GraphQL errors en procesarGuionAgente2:', result.errors);
        return null;
      }

      const response = result.data?.procesarGuionAgente2;
      if (!response) {
        console.error(' No se recibió respuesta de procesarGuionAgente2');
        return null;
      }

      console.log(' Guion procesado:', response.siguientePaso);
      return response;
    } catch (err) {
      console.error(' Error en procesarGuionAgente2:', err);
      return null;
    }
  }

  /**
   * 2. CONTINUAR CONVERSACIÓN
   * Maneja la respuesta del usuario (aprobación, rechazo, datos de envío)
   * 
   * @param respuestaUsuario - Texto de respuesta del usuario
   * @param sessionId - ID de sesión (opcional, usa el actual si no se proporciona)
   * @returns Siguiente paso del flujo
   */
  async continuarConversacion(
    respuestaUsuario: string,
    sessionId?: string
  ): Promise<ContinuarConversacionResponse | null> {
    const sid = sessionId || this.sessionId;

    const mutation = `
      mutation ContinuarConversacion($sessionId: String!, $respuestaUsuario: String!) {
        continuarConversacion(
          sessionId: $sessionId
          respuestaUsuario: $respuestaUsuario
        ) {
          success
          mensaje
          mejorOpcionId
          siguientePaso
          audioUrl
        }
      }
    `;

    try {
      console.log('📤 Enviando mutation continuarConversacion...');
      console.log('Variables:', { sessionId: sid, respuestaUsuario });
      
      const result = await graphQLFetch<{ continuarConversacion: ContinuarConversacionResponse }>(
        mutation,
        { sessionId: sid, respuestaUsuario }
      );

      console.log('📥 Resultado completo:', result);

      if (result.errors) {
        console.error(' GraphQL errors en continuarConversacion:', result.errors);
        console.error('Detalles:', JSON.stringify(result.errors, null, 2));
        return null;
      }

      const response = result.data?.continuarConversacion;
      if (!response) {
        console.error(' No se recibió respuesta de continuarConversacion');
        console.error('Data recibida:', result.data);
        return null;
      }

      console.log(' Conversación continuada:', response.siguientePaso);
      return response;
    } catch (err) {
      console.error(' Error en continuarConversacion:', err);
      if (err instanceof Error) {
        console.error('Stack trace:', err.stack);
      }
      return null;
    }
  }

  /**
   * HELPER: Crear guion simple desde texto del usuario
   * Útil para testing sin Agente 2 de visión
   * 
   * @param textoUsuario - Mensaje del usuario
   * @param productos - Lista de productos detectados (con barcodes)
   * @param preferenciasCustom - Preferencias extraídas del mensaje (opcional)
   * @returns Objeto GuionEntradaInput listo para procesar
   */
  crearGuionSimple(
    textoUsuario: string,
    productos: Array<{ 
      barcode: string; 
      nombre: string; 
      prioridad?: 'alta' | 'media' | 'baja';
      motivoSeleccion?: string;
    }>,
    preferenciasCustom?: Partial<PreferenciasUsuario>
  ): GuionEntradaInput {
    return {
      sessionId: this.sessionId,
      productos: productos.map(p => ({
        codigoBarras: p.barcode,
        nombreDetectado: p.nombre,
        prioridad: p.prioridad || 'media',
        motivoSeleccion: p.motivoSeleccion || 'Producto mencionado por usuario',
      })),
      preferencias: {
        estiloComunicacion: 'neutral',
        buscaOfertas: true,
        urgencia: 'media',
        ...preferenciasCustom, // Merge con preferencias extraídas
      },
      contexto: {
        tipoEntrada: 'texto',
        necesitaRecomendacion: true,
        intencionPrincipal: 'compra_directa',
      },
      textoOriginalUsuario: textoUsuario,
      resumenAnalisis: `Usuario busca: ${textoUsuario}`,
      confianzaProcesamiento: 0.85,
    };
  }
}

// Exportar instancia singleton
export const guionService = new GuionService();
