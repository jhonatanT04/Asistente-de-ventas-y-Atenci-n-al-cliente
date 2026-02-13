// src/services/orderGraphQLService.ts
/**
 * Servicio GraphQL para gestión de órdenes
 * Consume el backend OrderService a través de GraphQL
 */

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const GRAPHQL_ENDPOINT = `${API_BASE}/graphql`;

// ==================== TIPOS ====================

export interface OrderItem {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface OrderDetail {
  id: string;
  user_id: string;
  order_number: string;
  status: 'PENDING' | 'CONFIRMED' | 'PAID' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED';
  payment_status: string;
  total_amount: number;
  subtotal_amount: number;
  tax_amount: number;
  shipping_cost: number;
  item_count: number;
  created_at: string;
  updated_at: string;
  
  // Dirección de envío
  shipping_address: string;
  shipping_city?: string;
  shipping_state?: string;
  shipping_country?: string;
  shipping_zip?: string;
  
  // Contacto
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
  
  notes?: string;
  internal_notes?: string;
  
  // Items del pedido
  details: OrderItem[];
}

export interface OrderSummary {
  id: string;
  order_number: string;
  status: string;
  total_amount: number;
  item_count: number;
  created_at: string;
}

export interface CreateOrderInput {
  user_id: string;
  details: Array<{
    product_id: string;
    quantity: number;
  }>;
  shipping_address: string;
  shipping_city?: string;
  shipping_state?: string;
  shipping_country?: string;
  shipping_zip?: string;
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
  notes?: string;
  session_id?: string;
}

export interface CheckoutResponse {
  success: boolean;
  order_id?: string;
  message: string;
  order_total?: number;
  item_count?: number;
  error_code?: string;
}

interface GraphQLError {
  message: string;
  locations?: Array<{ line: number; column: number }>;
  path?: string[];
}

interface GraphQLResponse<T> {
  data?: T;
  errors?: GraphQLError[];
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

// ==================== ORDER GRAPHQL SERVICE ====================

export class OrderGraphQLService {
  /**
   * Obtiene un pedido por su ID con todos los detalles
   */
  async getOrderById(orderId: string): Promise<OrderDetail | null> {
    const query = `
      query GetOrder($orderId: ID!) {
        getOrder(orderId: $orderId) {
          id
          user_id
          order_number
          status
          payment_status
          total_amount
          subtotal_amount
          tax_amount
          shipping_cost
          item_count
          created_at
          updated_at
          shipping_address
          shipping_city
          shipping_state
          shipping_country
          shipping_zip
          contact_name
          contact_phone
          contact_email
          notes
          internal_notes
          details {
            id
            product_id
            product_name
            product_sku
            quantity
            unit_price
            subtotal
          }
        }
      }
    `;

    try {
      const result = await graphQLFetch<{ getOrder: OrderDetail }>(query, { orderId });

      if (result.errors) {
        console.error('GraphQL errors:', result.errors);
        return null;
      }

      return result.data?.getOrder || null;
    } catch (err) {
      console.error('Error en getOrderById:', err);
      return null;
    }
  }

  /**
   * Obtiene las órdenes de un usuario
   */
  async getOrdersByUser(userId: string, limit: number = 10, offset: number = 0): Promise<OrderSummary[]> {
    const query = `
      query GetUserOrders($userId: ID!, $limit: Int, $offset: Int) {
        getUserOrders(userId: $userId, limit: $limit, offset: $offset) {
          id
          order_number
          status
          total_amount
          item_count
          created_at
        }
      }
    `;

    try {
      const result = await graphQLFetch<{ getUserOrders: OrderSummary[] }>(query, {
        userId,
        limit,
        offset,
      });

      if (result.errors) {
        console.error('GraphQL errors:', result.errors);
        return [];
      }

      return result.data?.getUserOrders || [];
    } catch (err) {
      console.error('Error en getOrdersByUser:', err);
      return [];
    }
  }

  /**
   * Obtiene las órdenes más recientes (para admin)
   */
  async getRecentOrders(limit: number = 20, statusFilter?: string): Promise<OrderSummary[]> {
    const query = `
      query GetRecentOrders($limit: Int, $statusFilter: String) {
        getRecentOrders(limit: $limit, statusFilter: $statusFilter) {
          id
          order_number
          status
          total_amount
          item_count
          created_at
        }
      }
    `;

    try {
      const result = await graphQLFetch<{ getRecentOrders: OrderSummary[] }>(query, {
        limit,
        statusFilter,
      });

      if (result.errors) {
        console.error('GraphQL errors:', result.errors);
        return [];
      }

      return result.data?.getRecentOrders || [];
    } catch (err) {
      console.error('Error en getRecentOrders:', err);
      return [];
    }
  }

  /**
   * Crea una nueva orden
   */
  async createOrder(orderData: CreateOrderInput): Promise<CheckoutResponse> {
    const mutation = `
      mutation CreateOrder($input: CreateOrderInput!) {
        createOrder(input: $input) {
          success
          order_id
          message
          order_total
          item_count
          error_code
        }
      }
    `;

    try {
      const result = await graphQLFetch<{ createOrder: CheckoutResponse }>(mutation, {
        input: orderData,
      });

      if (result.errors) {
        console.error('GraphQL errors:', result.errors);
        return {
          success: false,
          message: 'Error al crear la orden: ' + result.errors[0].message,
          error_code: 'GRAPHQL_ERROR',
        };
      }

      return result.data?.createOrder || {
        success: false,
        message: 'No se recibió respuesta del servidor',
        error_code: 'NO_RESPONSE',
      };
    } catch (err) {
      console.error('Error en createOrder:', err);
      return {
        success: false,
        message: 'Error de conexión al crear la orden',
        error_code: 'CONNECTION_ERROR',
      };
    }
  }

  /**
   * Método simplificado para checkout desde el chat
   */
  async createOrderFromChat(
    userId: string,
    items: Array<{ product_id: string; quantity: number }>,
    shippingAddress: string,
    sessionId?: string,
    contactInfo?: {
      name?: string;
      phone?: string;
      email?: string;
    }
  ): Promise<CheckoutResponse> {
    const orderData: CreateOrderInput = {
      user_id: userId,
      details: items,
      shipping_address: shippingAddress,
      session_id: sessionId,
      contact_name: contactInfo?.name,
      contact_phone: contactInfo?.phone,
      contact_email: contactInfo?.email,
    };

    return this.createOrder(orderData);
  }

  /**
   * Actualiza el estado de una orden
   */
  async updateOrderStatus(
    orderId: string,
    newStatus: string,
    reason?: string
  ): Promise<{ success: boolean; message: string }> {
    const mutation = `
      mutation UpdateOrderStatus($orderId: ID!, $newStatus: String!, $reason: String) {
        updateOrderStatus(orderId: $orderId, newStatus: $newStatus, reason: $reason) {
          success
          message
        }
      }
    `;

    try {
      const result = await graphQLFetch<{
        updateOrderStatus: { success: boolean; message: string };
      }>(mutation, { orderId, newStatus, reason });

      if (result.errors) {
        console.error('GraphQL errors:', result.errors);
        return {
          success: false,
          message: 'Error actualizando el estado: ' + result.errors[0].message,
        };
      }

      return (
        result.data?.updateOrderStatus || {
          success: false,
          message: 'No se recibió respuesta del servidor',
        }
      );
    } catch (err) {
      console.error('Error en updateOrderStatus:', err);
      return {
        success: false,
        message: 'Error de conexión al actualizar el estado',
      };
    }
  }

  /**
   * Cancela una orden
   */
  async cancelOrder(
    orderId: string,
    reason?: string
  ): Promise<{ success: boolean; message: string }> {
    const mutation = `
      mutation CancelOrder($orderId: ID!, $reason: String) {
        cancelOrder(orderId: $orderId, reason: $reason) {
          success
          message
        }
      }
    `;

    try {
      const result = await graphQLFetch<{
        cancelOrder: { success: boolean; message: string };
      }>(mutation, { orderId, reason });

      if (result.errors) {
        console.error('GraphQL errors:', result.errors);
        return {
          success: false,
          message: 'Error cancelando la orden: ' + result.errors[0].message,
        };
      }

      return (
        result.data?.cancelOrder || {
          success: false,
          message: 'No se recibió respuesta del servidor',
        }
      );
    } catch (err) {
      console.error('Error en cancelOrder:', err);
      return {
        success: false,
        message: 'Error de conexión al cancelar la orden',
      };
    }
  }

  /**
   * Obtiene estadísticas de órdenes
   */
  async getOrderStats(userId?: string): Promise<{
    total_orders: number;
    total_revenue: number;
    status_breakdown: Record<string, number>;
    average_order_value: number;
  }> {
    const query = `
      query GetOrderStats($userId: ID) {
        getOrderStats(userId: $userId) {
          total_orders
          total_revenue
          status_breakdown
          average_order_value
        }
      }
    `;

    try {
      const result = await graphQLFetch<{
        getOrderStats: {
          total_orders: number;
          total_revenue: number;
          status_breakdown: Record<string, number>;
          average_order_value: number;
        };
      }>(query, { userId });

      if (result.errors) {
        console.error('GraphQL errors:', result.errors);
        return {
          total_orders: 0,
          total_revenue: 0,
          status_breakdown: {},
          average_order_value: 0,
        };
      }

      return (
        result.data?.getOrderStats || {
          total_orders: 0,
          total_revenue: 0,
          status_breakdown: {},
          average_order_value: 0,
        }
      );
    } catch (err) {
      console.error('Error en getOrderStats:', err);
      return {
        total_orders: 0,
        total_revenue: 0,
        status_breakdown: {},
        average_order_value: 0,
      };
    }
  }
}

// ==================== INSTANCIA SINGLETON ====================

export const orderGraphQLService = new OrderGraphQLService();

// Exportar también como default para importaciones flexibles
export default orderGraphQLService;