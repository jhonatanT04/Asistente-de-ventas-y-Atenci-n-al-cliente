// src/pages/OrderDetail/OrderDetailGraphQL.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './orderdetail.css';
import { 
  FiArrowLeft, FiPackage, FiMapPin, FiTruck, 
  FiCheck, FiClock, FiDownload, FiXCircle 
} from 'react-icons/fi';
import { orderGraphQLService, OrderDetail as OrderDetailType } from '../services/ordergraphql';

interface TimelineEvent {
  status: string;
  date: string;
  message: string;
  completed: boolean;
}

const OrderDetailGraphQL: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<OrderDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    loadOrderDetail();
  }, [orderId]);

  const loadOrderDetail = async () => {
    if (!orderId) return;
    
    try {
      setLoading(true);
      const orderData = await orderGraphQLService.getOrderById(orderId);
      setOrder(orderData);
    } catch (error) {
      console.error('Error cargando orden:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelOrder = async () => {
    if (!orderId || !window.confirm('¿Estás seguro de cancelar esta orden?')) return;
    
    try {
      setCancelling(true);
      const result = await orderGraphQLService.cancelOrder(
        orderId, 
        'Cancelado por el usuario desde la interfaz'
      );
      
      if (result.success) {
        alert('Orden cancelada exitosamente');
        loadOrderDetail(); // Recargar para ver el estado actualizado
      } else {
        alert(`Error: ${result.message}`);
      }
    } catch (error) {
      console.error('Error cancelando orden:', error);
      alert('Error al cancelar la orden');
    } finally {
      setCancelling(false);
    }
  };

  const getStatusInfo = (status: string) => {
    const statusMap: Record<string, { label: string; color: string; icon: any }> = {
      PENDING: { label: 'Pendiente', color: '#f59e0b', icon: FiClock },
      CONFIRMED: { label: 'Confirmado', color: '#3b82f6', icon: FiPackage },
      PAID: { label: 'Pagado', color: '#8b5cf6', icon: FiCheck },
      SHIPPED: { label: 'Enviado', color: '#8b5cf6', icon: FiTruck },
      DELIVERED: { label: 'Entregado', color: '#10b981', icon: FiCheck },
      CANCELLED: { label: 'Cancelado', color: '#ef4444', icon: FiXCircle }
    };
    return statusMap[status] || statusMap.PENDING;
  };

  const buildTimeline = (order: OrderDetailType): TimelineEvent[] => {
    const events: TimelineEvent[] = [];
    const now = new Date().toISOString();
    
    events.push({
      status: 'Pedido recibido',
      date: order.created_at,
      message: 'Tu pedido ha sido recibido y está siendo procesado',
      completed: true
    });

    if (order.status !== 'PENDING') {
      events.push({
        status: 'Confirmado',
        date: order.updated_at || order.created_at,
        message: 'Tu pedido ha sido confirmado',
        completed: true
      });
    }

    if (order.status === 'PAID' || order.status === 'SHIPPED' || order.status === 'DELIVERED') {
      events.push({
        status: 'Pagado',
        date: order.updated_at || order.created_at,
        message: 'Pago procesado exitosamente',
        completed: true
      });
    }

    if (order.status === 'SHIPPED' || order.status === 'DELIVERED') {
      events.push({
        status: 'Enviado',
        date: order.updated_at || order.created_at,
        message: 'Tu pedido está en camino',
        completed: true
      });
    }

    if (order.status === 'DELIVERED') {
      events.push({
        status: 'Entregado',
        date: order.updated_at || order.created_at,
        message: 'Pedido entregado exitosamente',
        completed: true
      });
    }

    if (order.status === 'CANCELLED') {
      events.push({
        status: 'Cancelado',
        date: order.updated_at || order.created_at,
        message: 'El pedido ha sido cancelado',
        completed: true
      });
    }

    return events;
  };

  if (loading) {
    return (
      <div className="order-detail-container">
        <div className="loading">Cargando detalle...</div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="order-detail-container">
        <div className="error-message">Orden no encontrada</div>
        <button className="back-button" onClick={() => navigate('/ordenes')}>
          <FiArrowLeft size={20} />
          Volver a Órdenes
        </button>
      </div>
    );
  }

  const statusInfo = getStatusInfo(order.status);
  const StatusIcon = statusInfo.icon;
  const timeline = buildTimeline(order);

  return (
    <div className="order-detail-container">
      {/* Header */}
      <div className="detail-header">
        <button className="back-button" onClick={() => navigate('/ordenes')}>
          <FiArrowLeft size={20} />
          Volver
        </button>

        <div className="header-info">
          <h1>Orden {order.order_number || `#${order.id.substring(0, 8)}`}</h1>
          <span 
            className="status-badge"
            style={{ backgroundColor: statusInfo.color }}
          >
            <StatusIcon size={16} />
            {statusInfo.label}
          </span>
        </div>

        <div className="header-date">
          Realizada el {new Date(order.created_at).toLocaleDateString('es-ES', {
            day: '2-digit',
            month: 'long',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>

      <div className="detail-content">
        {/* Timeline */}
        <div className="timeline-section">
          <h2>Estado del Pedido</h2>
          <div className="timeline">
            {timeline.map((event, index) => (
              <div 
                key={index} 
                className={`timeline-item ${event.completed ? 'completed' : 'pending'}`}
              >
                <div className="timeline-marker">
                  {event.completed ? <FiCheck size={16} /> : <FiClock size={16} />}
                </div>
                <div className="timeline-content">
                  <div className="timeline-status">{event.status}</div>
                  <div className="timeline-date">
                    {new Date(event.date).toLocaleDateString('es-ES', {
                      day: '2-digit',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                  <div className="timeline-message">{event.message}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Productos */}
        <div className="items-section">
          <h2>Productos ({order.item_count})</h2>
          <div className="items-list">
            {order.details.map(item => (
              <div key={item.id} className="item-card">
                <div className="item-image-placeholder">
                  <FiPackage size={40} />
                </div>
                <div className="item-info">
                  <h3>{item.product_name}</h3>
                  <p className="item-sku">SKU: {item.product_sku}</p>
                  <p className="item-quantity">Cantidad: {item.quantity}</p>
                  <p className="item-unit-price">Precio unitario: ${item.unit_price.toFixed(2)}</p>
                </div>
                <div className="item-price">
                  ${item.subtotal.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Dirección de envío */}
        <div className="shipping-section">
          <h2>
            <FiMapPin size={20} />
            Dirección de Envío
          </h2>
          <div className="shipping-address">
            {order.contact_name && <p className="address-name">{order.contact_name}</p>}
            <p>{order.shipping_address}</p>
            {(order.shipping_city || order.shipping_state || order.shipping_zip) && (
              <p>
                {order.shipping_city}
                {order.shipping_state && `, ${order.shipping_state}`}
                {order.shipping_zip && ` ${order.shipping_zip}`}
              </p>
            )}
            {order.shipping_country && <p>{order.shipping_country}</p>}
            {order.contact_phone && <p className="address-phone">{order.contact_phone}</p>}
            {order.contact_email && <p className="address-email">{order.contact_email}</p>}
          </div>
        </div>

        {/* Resumen de pago */}
        <div className="summary-section">
          <h2>Resumen de Pago</h2>
          <div className="summary-details">
            <div className="summary-row">
              <span>Subtotal</span>
              <span>${order.subtotal_amount.toFixed(2)}</span>
            </div>
            <div className="summary-row">
              <span>Envío</span>
              <span>${order.shipping_cost.toFixed(2)}</span>
            </div>
            <div className="summary-row">
              <span>Impuestos</span>
              <span>${order.tax_amount.toFixed(2)}</span>
            </div>
            <div className="summary-row total">
              <span>Total</span>
              <span>${order.total_amount.toFixed(2)}</span>
            </div>
          </div>
          <div className="payment-status">
            Estado de pago: <strong>{order.payment_status}</strong>
          </div>
        </div>

        {/* Notas */}
        {order.notes && (
          <div className="notes-section">
            <h2>Notas del pedido</h2>
            <p>{order.notes}</p>
          </div>
        )}

        {/* Acciones */}
        <div className="actions-section">
          <button className="action-button primary">
            <FiDownload size={20} />
            Descargar Factura
          </button>
          <button className="action-button secondary">
            Contactar Soporte
          </button>
          {order.status !== 'CANCELLED' && order.status !== 'DELIVERED' && (
            <button 
              className="action-button danger"
              onClick={handleCancelOrder}
              disabled={cancelling}
            >
              <FiXCircle size={20} />
              {cancelling ? 'Cancelando...' : 'Cancelar Orden'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default OrderDetailGraphQL;