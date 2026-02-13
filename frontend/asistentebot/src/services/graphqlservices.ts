// src/services/graphqlservices.ts
/**
 * Servicio GraphQL + REST helpers para comunicación con el backend.
 * Incluye: ChatService, ProductService, AuthService, OrderService
 */

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const GRAPHQL_ENDPOINT = `${API_BASE}/graphql`;

interface GraphQLError {
  message: string;
  locations?: Array<{ line: number; column: number }>;
  path?: string[];
}

interface GraphQLResponse<T> {
  data?: T;
  errors?: GraphQLError[];
}

// ==================== TIPOS ====================

export interface SemanticSearchResult {
  answer: string;
  query: string;
  error: string | null;
  audioUrl?: string;
}

export interface Product {
  id: string;
  productName: string;
  unitCost: number;
  quantityAvailable: number;
  stockStatus: number;
  warehouseLocation: string;
  shelfLocation?: string;
  batchNumber?: string;
  barcode?: string;
}

export interface Order {
  id: string;
  user_id: string;
  total_amount: number;
  status: string;
  created_at: string;
  shipping_address: string;
  notes?: string;
}

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: 'USER' | 'AGENT' | 'SYSTEM';
  message: string;
  createdAt: string;
  metadata?: string;
  orderId?: string;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  total: number;
  hasMore: boolean;
}

// ==================== HELPERS ====================

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function graphQLFetch<T>(query: string, variables?: Record<string, any>): Promise<GraphQLResponse<T>> {
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
    throw new Error(`HTTP error! status: ${res.status}`);
  }

  return res.json();
}

// ==================== CHAT SERVICE ====================

export class ChatService {
  private sessionId: string;

  constructor() {
    this.sessionId = this.getOrCreateSessionId();
  }

  private getOrCreateSessionId(): string {
    let sessionId = localStorage.getItem('chat_session_id');
    if (!sessionId) {
      sessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      localStorage.setItem('chat_session_id', sessionId);
    }
    return sessionId;
  }

  async sendMessage(userMessage: string): Promise<SemanticSearchResult> {
    const query = `
      query Chat($query: String!, $sessionId: String) {
        semanticSearch(query: $query, sessionId: $sessionId) {
          answer
          query
          error
          audioUrl
        }
      }
    `;
    const variables = { query: userMessage, sessionId: this.sessionId };

    try {
      const result = await graphQLFetch<{ semanticSearch: SemanticSearchResult }>(query, variables);

      if (result.errors) {
        console.error('GraphQL errors:', result.errors);
        return {
          answer: 'Lo siento, hubo un error al procesar tu mensaje. Por favor intenta de nuevo.',
          query: userMessage,
          error: 'graphql_error',
        };
      }

      const res = result.data?.semanticSearch;
      if (!res) {
        return {
          answer: 'No se recibió respuesta del servidor.',
          query: userMessage,
          error: 'no_response',
        };
      }

      return res;
    } catch (err) {
      console.error('Error en ChatService.sendMessage:', err);
      return {
        answer: 'No pude conectarme al servidor. Revisa tu conexión.',
        query: userMessage,
        error: 'connection_error',
      };
    }
  }

  resetSession(): void {
    localStorage.removeItem('chat_session_id');
    this.sessionId = this.getOrCreateSessionId();
  }

  getSessionId(): string {
    return this.sessionId;
  }

  async getChatHistory(
    sessionId?: string,
    limit: number = 100
  ): Promise<{ messages: ChatMessage[]; total: number; hasMore: boolean }> {
    const sid = sessionId || this.sessionId;
    const query = `
      query GetChatHistory($sessionId: String!, $limit: Int) {
        getChatHistory(sessionId: $sessionId, limit: $limit) {
          messages {
            id
            sessionId
            role
            message
            createdAt
            metadata
            orderId
          }
          total
          hasMore
        }
      }
    `;

    try {
      const result = await graphQLFetch<{ getChatHistory: ChatHistoryResponse }>(
        query,
        { sessionId: sid, limit }
      );

      if (result.errors || !result.data) {
        console.error('Error obteniendo historial:', result.errors);
        return { messages: [], total: 0, hasMore: false };
      }

      return result.data.getChatHistory;
    } catch (err) {
      console.error('Error en ChatService.getChatHistory:', err);
      return { messages: [], total: 0, hasMore: false };
    }
  }
}

// ==================== PRODUCT SERVICE ====================

export class ProductService {
  async listProducts(limit: number = 20): Promise<Product[]> {
    const query = `
      query ListProducts($limit: Int) {
        listProducts(limit: $limit) {
          id
          productName
          unitCost
          quantityAvailable
          stockStatus
          warehouseLocation
          shelfLocation
          batchNumber
          barcode
        }
      }
    `;
    try {
      const result = await graphQLFetch<{ listProducts: Product[] }>(query, { limit });
      if (result.errors) {
        console.error('GraphQL errors:', result.errors);
        return [];
      }
      return result.data?.listProducts || [];
    } catch (err) {
      console.error('Error en ProductService.listProducts:', err);
      return [];
    }
  }

  async searchProducts(searchTerm: string, limit = 20): Promise<Product[]> {
    const all = await this.listProducts(limit);
    if (!searchTerm.trim()) return all;
    const s = searchTerm.toLowerCase();
    return all.filter(p =>
      (p.productName || '').toLowerCase().includes(s) ||
      (p.batchNumber || '').toLowerCase().includes(s)
    );
  }
}

// ==================== AUTH SERVICE (REST) ====================

export class AuthService {
  private base = API_BASE;

  private isEmail(identifier: string) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(identifier);
  }

  async login(identifier: string, password: string): Promise<{ access_token?: string; error?: any }> {
    const payload: Record<string, any> = { password };
    if (this.isEmail(identifier)) payload.email = identifier;
    else payload.username = identifier;

    try {
      const res = await fetch(`${this.base}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        return { error: data };
      }
      if (data.access_token) {
        localStorage.setItem('access_token', data.access_token);
      }
      return { access_token: data.access_token };
    } catch (err) {
      console.error('AuthService.login error:', err);
      return { error: err };
    }
  }

  async register(username: string, email: string, password: string) {
    try {
      const res = await fetch(`${this.base}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      });
      const data = await res.json();
      return res.ok ? data : Promise.reject(data);
    } catch (err) {
      console.error('AuthService.register error:', err);
      throw err;
    }
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  getUserFromToken(): { id: string; username: string; email: string; role: number } | null {
    const token = this.getToken();
    if (!token) return null;
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      const payload = JSON.parse(jsonPayload);
      return {
        id: payload.id,
        username: payload.username,
        email: payload.email,
        role: payload.role,
      };
    } catch (err) {
      console.error('AuthService.getUserFromToken error:', err);
      return null;
    }
  }
}

// ==================== ORDER SERVICE (REST) ====================

export class OrderService {
  private base = API_BASE;

  private headers() {
    return { 'Content-Type': 'application/json', ...getAuthHeader() };
  }

  async getMyOrders(): Promise<Order[]> {
    try {
      const res = await fetch(`${this.base}/my-orders`, { headers: this.headers() });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      return res.json();
    } catch (err) {
      console.error('OrderService.getMyOrders error:', err);
      return [];
    }
  }

  async getOrderById(orderId: string): Promise<Order | null> {
    try {
      const res = await fetch(`${this.base}/orders/${orderId}`, { headers: this.headers() });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      return res.json();
    } catch (err) {
      console.error('OrderService.getOrderById error:', err);
      return null;
    }
  }

  async createOrder(payload: any): Promise<Order | null> {
    try {
      const res = await fetch(`${this.base}/orders`, {
        method: 'POST',
        headers: this.headers(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(JSON.stringify(data));
      }
      return res.json();
    } catch (err) {
      console.error('OrderService.createOrder error:', err);
      return null;
    }
  }

  async cancelOrder(orderId: string): Promise<boolean> {
    try {
      const res = await fetch(`${this.base}/orders/${orderId}`, {
        method: 'DELETE',
        headers: this.headers(),
      });
      return res.ok;
    } catch (err) {
      console.error('OrderService.cancelOrder error:', err);
      return false;
    }
  }
}

// ==================== INSTANCIAS ====================

export const chatService = new ChatService();
export const productService = new ProductService();
export const authService = new AuthService();
export const orderService = new OrderService();


// ==================== RAG SERVICE (cliente) ====================
export interface RAGDoc {
  content: string;
  category: string;
  relevance_score: number;
  source: string; // "chunks" | "faqs" | "unknown"
}

export class RAGService {
  private base = API_BASE;

  /**
   * Llama a la query GraphQL `semanticSearch` (si tu backend expone contexto/RAG vía GraphQL).
   * Devuelve el texto de respuesta del LLM y un arreglo vacío de docs porque la query estándar
   * devuelve solo `answer`. Si tu backend expone una query REST/GraphQL distinta para RAG docs,
   * actualiza la query/endpoint aquí.
   */
  async semanticSearch(query: string, sessionId?: string): Promise<{ answer: string; query: string; error: string | null; audioUrl?: string }> {
    const q = `
      query Semantic($q: String!, $sessionId: String) {
        semanticSearch(query: $q, sessionId: $sessionId) {
          answer
          query
          error
          audioUrl
        }
      }
    `;
    try {
      const res = await graphQLFetch<{ semanticSearch: { answer: string; query: string; error: string | null } }>(q, { q: query, sessionId });
      if (res.errors) {
        console.error('RAG.semanticSearch GraphQL errors:', res.errors);
        return { answer: 'Error en consulta semántica', query, error: 'graphql_error' };
      }
      const payload = res.data?.semanticSearch;
      return payload ?? { answer: 'No hay respuesta', query, error: 'no_response' };
    } catch (err) {
      console.error('RAG.semanticSearch error:', err);
      return { answer: 'Error de conexión con el servidor RAG', query, error: 'connection_error' };
    }
  }

  /**
   * Intento de obtener documentos RAG (si tu backend expone REST /rag/search o /rag/context).
   * Si el endpoint no existe, devuelve [].
   */
  async searchDocs(query: string, k: number = 3): Promise<RAGDoc[]> {
    try {
      const url = `${this.base}/rag/search?query=${encodeURIComponent(query)}&k=${k}`;
      const res = await fetch(url, { headers: { ...getAuthHeader(), 'Content-Type': 'application/json' } });
      if (!res.ok) {
        // Endpoint no disponible o no autorizada: retornar vacío en lugar de crash
        console.warn(`RAG.searchDocs REST not available (status ${res.status})`);
        return [];
      }
      const data = await res.json();
      // Esperamos que el backend retorne lista de documentos con fields: content, category, relevance_score, source
      return Array.isArray(data) ? data as RAGDoc[] : [];
    } catch (err) {
      console.error('RAG.searchDocs error:', err);
      return [];
    }
  }

  /**
   * Obtener contexto formateado (intenta REST /rag/context; si no existe, construye a partir de searchDocs).
   */
  async getContextForQuery(query: string, maxResults: number = 3): Promise<string> {
    try {
      const url = `${this.base}/rag/context?query=${encodeURIComponent(query)}&max_results=${maxResults}`;
      const res = await fetch(url, { headers: { ...getAuthHeader(), 'Content-Type': 'application/json' } });
      if (res.ok) {
        const text = await res.text();
        return text;
      }
    } catch (err) {
      // ignore - fallback below
    }

    // Fallback: usar searchDocs y formatear
    const docs = await this.searchDocs(query, maxResults);
    if (!docs.length) return 'No se encontró información relevante en la base de conocimiento.';

    const parts = ['=== INFORMACIÓN RELEVANTE DE LA BASE DE CONOCIMIENTO ===\n'];
    docs.slice(0, maxResults).forEach((d, i) => {
      parts.push(
        `\n[Documento ${i + 1} - ${d.category} | Relevancia: ${d.relevance_score}]\n${d.content}\n`
      );
    });
    return parts.join('\n');
  }

  /**
   * Reconstruye índice (llama POST /rag/rebuild). Devuelve true si ok.
   */
  async rebuildIndex(): Promise<boolean> {
    try {
      const res = await fetch(`${this.base}/rag/rebuild`, {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
      });
      return res.ok;
    } catch (err) {
      console.error('RAG.rebuildIndex error:', err);
      return false;
    }
  }

  /**
   * Obtener estadísticas del RAG (GET /rag/stats). Si no existe, devuelve objeto por defecto.
   */
  async getStats(): Promise<Record<string, any>> {
    try {
      const res = await fetch(`${this.base}/rag/stats`, {
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
      });
      if (!res.ok) return { total_documents: 0 };
      return res.json();
    } catch (err) {
      console.error('RAG.getStats error:', err);
      return { total_documents: 0 };
    }
  }
}

export const ragService = new RAGService();