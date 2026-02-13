// src/hooks/useOrderCreation.ts
import { useState, useCallback } from 'react';
import { orderGraphQLService, CheckoutResponse } from '../services/ordergraphql';
import { authService } from '../services/graphqlservices';

interface CartItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
}

interface ShippingInfo {
  address: string;
  city?: string;
  state?: string;
  country?: string;
  zip?: string;
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
}

export interface OrderCreationState {
  isCreating: boolean;
  error: string | null;
  success: boolean;
  orderResult: CheckoutResponse | null;
}

export const useOrderCreation = () => {
  const [state, setState] = useState<OrderCreationState>({
    isCreating: false,
    error: null,
    success: false,
    orderResult: null,
  });

  /**
   * Crea una orden desde el carrito del chat
   */
  const createOrderFromCart = useCallback(
    async (
      cartItems: CartItem[],
      shippingInfo: ShippingInfo,
      sessionId?: string
    ): Promise<CheckoutResponse> => {
      setState({
        isCreating: true,
        error: null,
        success: false,
        orderResult: null,
      });

      try {
        // Obtener usuario actual
        const user = authService.getUserFromToken();
        if (!user) {
          throw new Error('Usuario no autenticado');
        }

        // Convertir items del carrito al formato esperado
        const orderItems = cartItems.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity,
        }));

        // Crear la orden
        const result = await orderGraphQLService.createOrderFromChat(
          user.id,
          orderItems,
          shippingInfo.address,
          sessionId,
          {
            name: shippingInfo.contact_name,
            phone: shippingInfo.contact_phone,
            email: shippingInfo.contact_email,
          }
        );

        setState({
          isCreating: false,
          error: result.success ? null : result.message,
          success: result.success,
          orderResult: result,
        });

        return result;
      } catch (error: any) {
        const errorMessage = error.message || 'Error inesperado al crear la orden';
        
        setState({
          isCreating: false,
          error: errorMessage,
          success: false,
          orderResult: null,
        });

        return {
          success: false,
          message: errorMessage,
          error_code: 'CREATION_ERROR',
        };
      }
    },
    []
  );

  /**
   * Resetea el estado
   */
  const reset = useCallback(() => {
    setState({
      isCreating: false,
      error: null,
      success: false,
      orderResult: null,
    });
  }, []);

  return {
    ...state,
    createOrderFromCart,
    reset,
  };
};