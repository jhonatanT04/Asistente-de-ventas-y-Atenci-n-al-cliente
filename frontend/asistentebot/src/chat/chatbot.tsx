// chatbot.tsx - CON INTEGRACIÓN DE ÓRDENES
import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { useNavigate } from 'react-router-dom';
import { chatService, ragService, authService } from '../services/graphqlservices';
import { guionService } from '../services/guionService';
import { useOrderCreation } from '../services/userordercreation';
import type { SemanticSearchResult, RAGDoc } from '../services/graphqlservices';
import { AudioPlayer } from '../components/AudioPlayer';
import './chatbot.css';
import {
  FiMessageCircle,
  FiX,
  FiSend,
  FiAlertCircle,
  FiRefreshCw,
  FiFileText,
  FiCheck,
  FiClock,
  FiShoppingCart,
  FiPackage,
  FiTrash2
} from 'react-icons/fi';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  error?: string | null;
  ragDocs?: RAGDoc[];
  status?: 'sending' | 'sent' | 'error';
  audioUrl?: string;  // URL del audio
  metadata?: {
    type?: 'order_confirmation' | 'order_created' | 'error' | 'cart_updated';
    order_id?: string;
    order_total?: number;
    products_added?: CartItem[];
  };
}

interface QuickAction {
  id: string;
  label: string;
  message: string;
}

interface CartItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
}

const ChatBot: React.FC = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showRagDocs, setShowRagDocs] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  
  // Estados para el carrito y checkout
  const [cart, setCart] = useState<CartItem[]>([]);
  const [showCart, setShowCart] = useState(false);
  const [checkoutFlow, setCheckoutFlow] = useState<{
    active: boolean;
    step: 'address' | 'confirm' | 'processing' | null;
    shippingAddress?: string;
    contactName?: string;
    contactPhone?: string;
    contactEmail?: string;
  }>({
    active: false,
    step: null
  });

  // Estados para el flujo de Guion (Agente 2 → Agente 3)
  const [guionFlow, setGuionFlow] = useState<{
    active: boolean;
    mejorOpcionId?: string;
    sessionId?: string;
  }>({
    active: false
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatMessagesRef = useRef<HTMLDivElement>(null);

  // Hook de creación de órdenes
  const { 
    isCreating, 
    error: orderError, 
    success: orderSuccess, 
    orderResult, 
    createOrderFromCart,
    reset: resetOrderState 
  } = useOrderCreation();

  // Quick actions para sugerencias rápidas
  const quickActions: QuickAction[] = [
    { id: '1', label: '📦 Ver productos', message: 'list_products_action' } // Acción especial
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setUnreadCount(0);
    }
  }, [isOpen]);

  // Simular mensajes no leídos cuando el chat está cerrado
  useEffect(() => {
    if (!isOpen && messages.length > 1) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.sender === 'bot') {
        setUnreadCount(prev => prev + 1);
      }
    }
  }, [messages, isOpen]);

  // Cargar historial de chat al iniciar
  useEffect(() => {
    const loadChatHistory = async () => {
      if (historyLoaded) return;

      const token = authService.getToken();

      // Si no hay token, mostrar mensaje de bienvenida
      if (!token) {
        setMessages([{
          id: '1',
          text: '¡Hola! Soy **Alex**, tu asistente de ventas. 👋\n\nEstoy aquí para ayudarte con:\n- Información de productos\n- Recomendaciones personalizadas\n- Agregar productos al carrito\n- Realizar pedidos\n- Preguntas sobre envíos y pagos\n\n¿En qué puedo ayudarte hoy?',
          sender: 'bot',
          timestamp: new Date(),
          status: 'sent'
        }]);
        setHistoryLoaded(true);
        return;
      }

      setIsLoadingHistory(true);

      try {
        const { messages: historicalMessages } = await chatService.getChatHistory(
          chatService.getSessionId(),
          50
        );

        if (historicalMessages.length > 0) {
          const formattedMessages: Message[] = historicalMessages.map(msg => ({
            id: msg.id,
            text: msg.message,
            sender: msg.role === 'USER' ? 'user' : 'bot',
            timestamp: new Date(msg.createdAt),
            status: 'sent'
          }));

          setMessages(formattedMessages);

          // Restaurar estado de guionFlow si el último mensaje es de guion
          const lastAgentMessage = historicalMessages
            .filter(m => m.role === 'AGENT')
            .reverse()[0];

          if (lastAgentMessage && lastAgentMessage.metadata) {
            try {
              const metadata = JSON.parse(lastAgentMessage.metadata);

              // Si tiene mejor_opcion_id y siguiente_paso, es un flujo de guion activo
              if (metadata.mejor_opcion_id && metadata.siguiente_paso) {
                const siguientePaso = metadata.siguiente_paso;

                // Solo restaurar si el flujo NO ha terminado
                if (siguientePaso !== 'nueva_conversacion' && siguientePaso !== 'orden_completada') {
                  setGuionFlow({
                    active: true,
                    mejorOpcionId: metadata.mejor_opcion_id,
                    sessionId: chatService.getSessionId()
                  });
                  console.log('✅ Flujo de guion restaurado:', {
                    mejorOpcionId: metadata.mejor_opcion_id,
                    siguientePaso: siguientePaso
                  });
                }
              }
            } catch (e) {
              // Metadata no es JSON válido, ignorar
            }
          }
        } else {
          setMessages([{
            id: '1',
            text: '¡Hola! Soy **Alex**, tu asistente de ventas. 👋\n\nEstoy aquí para ayudarte con:\n- Información de productos\n- Recomendaciones personalizadas\n- Agregar productos al carrito\n- Realizar pedidos\n- Preguntas sobre envíos y pagos\n\n¿En qué puedo ayudarte hoy?',
            sender: 'bot',
            timestamp: new Date(),
            status: 'sent'
          }]);
        }
      } catch (error) {
        console.error('Error cargando historial:', error);
        setMessages([{
          id: '1',
          text: '¡Hola! Soy **Alex**, tu asistente de ventas. 👋\n\nEstoy aquí para ayudarte con:\n- Información de productos\n- Recomendaciones personalizadas\n- Agregar productos al carrito\n- Realizar pedidos\n- Preguntas sobre envíos y pagos\n\n¿En qué puedo ayudarte hoy?',
          sender: 'bot',
          timestamp: new Date(),
          status: 'sent'
        }]);
      } finally {
        setIsLoadingHistory(false);
        setHistoryLoaded(true);
      }
    };

    loadChatHistory();
  }, []);

  // Calcular total del carrito
  const cartTotal = cart.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);

  const addMessage = (text: string, sender: 'user' | 'bot', metadata?: any, audioUrl?: string) => {
    const newMessage: Message = {
      id: `msg-${Date.now()}-${Math.random()}`,
      text,
      sender,
      timestamp: new Date(),
      status: 'sent',
      metadata,
      audioUrl
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const detectCartUpdates = (botResponse: string, rawResponse?: any) => {
    // Patrones para detectar productos agregados
    // Ejemplo: "Agregué Laptop Gaming x2 (ID: abc-123, Precio: $1299.99)"
    const addedPattern = /Agregué (.+?) x(\d+) \(ID: ([a-f0-9-]+)(?:, Precio: \$([0-9.]+))?\)/gi;
    const matches = Array.from(botResponse.matchAll(addedPattern));
    
    if (matches.length > 0) {
      const newItems: CartItem[] = matches.map(match => ({
        product_id: match[3],
        product_name: match[1],
        quantity: parseInt(match[2]),
        unit_price: parseFloat(match[4] || '0')
      }));
      
      setCart(prev => {
        const updated = [...prev];
        newItems.forEach(newItem => {
          const existingIndex = updated.findIndex(item => item.product_id === newItem.product_id);
          if (existingIndex >= 0) {
            updated[existingIndex].quantity += newItem.quantity;
          } else {
            updated.push(newItem);
          }
        });
        return updated;
      });

      // Mensaje de confirmación
      setTimeout(() => {
        addMessage(
          `✅ **Carrito actualizado**\n\nProductos en el carrito: ${cart.length + newItems.length}\nTotal: $${(cartTotal + newItems.reduce((s, i) => s + (i.unit_price * i.quantity), 0)).toFixed(2)}`,
          'bot',
          { type: 'cart_updated', products_added: newItems }
        );
      }, 500);
    }

    // También detectar si el bot menciona productos de forma estructurada
    // (ajusta esto según cómo tu backend devuelva la info)
  };

  const detectCheckoutIntent = (userMessage: string): boolean => {
    const checkoutKeywords = [
      'comprar', 'ordenar', 'pedido', 'checkout',
      'finalizar compra', 'confirmar orden', 'quiero comprar',
      'realizar pedido', 'hacer pedido', 'proceder al pago'
    ];
    
    return checkoutKeywords.some(keyword => 
      userMessage.toLowerCase().includes(keyword)
    );
  };

  /**
   * NUEVA FUNCIÓN: Detecta si el usuario menciona productos de la BD
   * Busca nombres de productos conocidos (Adidas, Nike, etc.)
   */
  const detectProductMentions = (userMessage: string): Array<{
    barcode: string; 
    nombre: string; 
    prioridad: 'alta' | 'media' | 'baja';
    motivoSeleccion: string;
  }> => {
    const message = userMessage.toLowerCase();
    const detectedProducts: Array<{
      barcode: string; 
      nombre: string; 
      prioridad: 'alta' | 'media' | 'baja';
      motivoSeleccion: string;
    }> = [];

    // Base de productos conocidos (según init_db_2.py)
    const productDatabase = [
      { 
        barcode: '7501234567891', 
        nombre: 'Nike Air Max 90', 
        keywords: ['air max', 'airmax', 'air max 90'],
        descripcion: 'Zapatilla clásica, buen precio'
      },
      { 
        barcode: '7501234567895', 
        nombre: 'Nike Air Force 1 \'07', 
        keywords: ['air force', 'airforce', 'force 1'],
        descripcion: 'Muy popular, estilo icónico'
      },
      { 
        barcode: '7501234567894', 
        nombre: 'Nike Court Vision Low', 
        keywords: ['court vision', 'courtvision'],
        descripcion: 'Alternativa económica con descuento'
      },
      { 
        barcode: '8806098934474', 
        nombre: 'Adidas Ultraboost Light', 
        keywords: ['ultraboost', 'ultra boost'],
        descripcion: 'Máximo confort para correr'
      },
      { 
        barcode: '8806098934475', 
        nombre: 'Adidas Supernova 3', 
        keywords: ['supernova'],
        descripcion: 'Excelente relación calidad-precio'
      },
      { 
        barcode: '8806098934478', 
        nombre: 'Adidas Samba OG', 
        keywords: ['samba'],
        descripcion: 'Estilo casual versátil'
      },
      { 
        barcode: '7501234567890', 
        nombre: 'Nike Air Zoom Pegasus 40', 
        keywords: ['pegasus', 'zoom pegasus'],
        descripcion: 'Ideal para entrenamientos'
      },
      { 
        barcode: '7501234567893', 
        nombre: 'Nike ZoomX Vaporfly 3', 
        keywords: ['vaporfly', 'zoomx'],
        descripcion: 'Alto rendimiento para competencias'
      },
    ];

    productDatabase.forEach((product, index) => {
      const isMainProduct = product.keywords.some(kw => message.includes(kw));
      if (isMainProduct) {
        // Asignar prioridad según orden de aparición y mención explícita
        let prioridad: 'alta' | 'media' | 'baja';
        if (detectedProducts.length === 0) {
          prioridad = 'alta'; // Primer producto mencionado
        } else if (detectedProducts.length === 1) {
          prioridad = 'media'; // Segundo producto
        } else {
          prioridad = 'baja'; // Tercer producto o más
        }

        detectedProducts.push({
          barcode: product.barcode,
          nombre: product.nombre,
          prioridad: prioridad,
          motivoSeleccion: product.descripcion
        });
      }
    });

    return detectedProducts;
  };

  /**
   * NUEVA FUNCIÓN: Detecta intención de comparación/recomendación
   */
  const detectComparisonIntent = (userMessage: string): boolean => {
    const comparisonKeywords = [
      'cual es mejor', 'cual me recomiendas', 'comparar', 'diferencia',
      'cual elegir', 'que me aconsejas', 'recomienda', 'recomendacion',
      'mejor opcion', 'cual compro'
    ];
    
    return comparisonKeywords.some(keyword => 
      userMessage.toLowerCase().includes(keyword)
    );
  };

  /**
   * 🆕 NUEVA FUNCIÓN: Extrae preferencias del mensaje del usuario
   */
  const extractPreferences = (userMessage: string) => {
    const message = userMessage.toLowerCase();
    const preferences: any = {
      estiloComunicacion: 'neutral',
      buscaOfertas: true,
      urgencia: 'media'
    };

    // Extraer presupuesto
    const budgetMatch = message.match(/\$(\d+)/); // Busca $150, $200, etc.
    if (budgetMatch) {
      preferences.presupuestoMaximo = parseInt(budgetMatch[1]);
    }

    // Extraer uso previsto
    if (message.includes('regalo')) {
      const giftContext = message.match(/regalo para ([\w\s]+?)(?:,|\.|$)/i);
      preferences.usoPrevisto = giftContext ? `Regalo para ${giftContext[1].trim()}` : 'Regalo';
    } else if (message.includes('correr') || message.includes('running')) {
      preferences.usoPrevisto = 'Running/Entrenamiento';
    } else if (message.includes('casual') || message.includes('diario')) {
      preferences.usoPrevisto = 'Uso casual diario';
    } else if (message.includes('competencia') || message.includes('maratón')) {
      preferences.usoPrevisto = 'Competencias/Maratón';
    }

    // Extraer urgencia
    if (message.includes('urgente') || message.includes('rápido') || message.includes('ya')) {
      preferences.urgencia = 'alta';
    } else if (message.includes('sin prisa') || message.includes('cuando sea')) {
      preferences.urgencia = 'baja';
    }

    // Detectar si busca ofertas
    if (message.includes('oferta') || message.includes('descuento') || message.includes('promo') || message.includes('barato')) {
      preferences.buscaOfertas = true;
    }

    return preferences;
  };

  /**
   *  NUEVA FUNCIÓN: Maneja el flujo de guion (procesarGuionAgente2)
   */
  const handleGuionFlow = async (
    userMessage: string, 
    detectedProducts: Array<{barcode: string; nombre: string; prioridad: 'alta' | 'media' | 'baja'; motivoSeleccion: string}>
  ) => {
    setIsTyping(true);
    
    try {
      console.log(' Iniciando flujo de guion con productos:', detectedProducts);

      // Extraer preferencias del mensaje
      const preferences = extractPreferences(userMessage);
      console.log(' Preferencias extraídas:', preferences);

      // Crear el guion con los productos detectados y preferencias
      const guion = guionService.crearGuionSimple(userMessage, detectedProducts, preferences);
      
      // Llamar al endpoint de Felipe
      const response = await guionService.procesarGuionAgente2(guion);

      if (!response) {
        addMessage(
          ' No pude procesar tu solicitud. Intenta de nuevo.',
          'bot'
        );
        setIsTyping(false);
        return;
      }

      console.log(' Respuesta del guion:', response);

      // Activar flujo de guion
      setGuionFlow({
        active: true,
        mejorOpcionId: response.mejorOpcionId,
        sessionId: guion.sessionId
      });

      // Formatear mensaje con los productos recomendados
      let mensaje = `${response.mensaje}\n\n`;
      
      if (response.productos && response.productos.length > 0) {
        mensaje += '**Productos comparados:**\n\n';
        response.productos.forEach((prod, idx) => {
          const emoji = prod.id === response.mejorOpcionId ? '⭐' : '•';
          mensaje += `${emoji} **${prod.productName}**\n`;
          mensaje += `   Precio: $${prod.finalPrice}`;
          if (prod.isOnSale) {
            mensaje += ` ~~$${prod.unitCost}~~ (${prod.discountPercent}% OFF)`;
          }
          mensaje += `\n   Score: ${prod.recommendationScore}/100\n`;
          mensaje += `   ${prod.reason}\n\n`;
        });
      }

      if (response.siguientePaso === 'confirmar_compra') {
        mensaje += '\n¿Te interesa este producto? Responde **"sí"** o **"no"**.';
      }

      addMessage(mensaje, 'bot', undefined, response.audioUrl);
      setIsTyping(false);

    } catch (error) {
      console.error('❌ Error en handleGuionFlow:', error);
      addMessage(
        '❌ Hubo un error procesando tu solicitud. Por favor, intenta de nuevo.',
        'bot'
      );
      setIsTyping(false);
    }
  };

  /**
   * NUEVA FUNCIÓN: Maneja la conversación del guion (continuarConversacion)
   */
  const handleGuionConversation = async (userMessage: string) => {
    setIsTyping(true);

    try {
      console.log('💬 Continuando conversación de guion:', userMessage);
      console.log('📋 Session ID:', guionFlow.sessionId);

      const response = await guionService.continuarConversacion(
        userMessage,
        guionFlow.sessionId
      );

      if (!response) {
        console.error('❌ Response is null or undefined');
        addMessage(
          '❌ No pude procesar tu respuesta. Por favor, intenta de nuevo.',
          'bot'
        );
        setIsTyping(false);
        return;
      }

      console.log('📥 Respuesta de continuación:', response);

      // Mostrar mensaje del bot
      let mensaje = response.mensaje;

      if (response.siguientePaso === 'solicitar_datos_envio') {
        mensaje += '\n\n📍 Por favor, indícame:\n- Talla\n- Dirección de envío';
        
      } else if (response.siguientePaso === 'ir_a_checkout') {
        mensaje += '\n\n✅ ¡Listo para procesar tu compra!';
        // Desactivar flujo de guion
        setGuionFlow({ active: false });
        
      } else if (response.siguientePaso === 'nueva_conversacion') {
        // Sin más opciones
        setGuionFlow({ active: false });
        
      } else if (response.siguientePaso === 'confirmar_compra') {
        // Hay alternativa
        mensaje += '\n\n¿Te interesa esta opción? Responde **"sí"** o **"no"**.';
        setGuionFlow(prev => ({
          ...prev,
          mejorOpcionId: response.mejorOpcionId
        }));
      }

      addMessage(mensaje, 'bot', undefined, response.audioUrl);
      setIsTyping(false);

    } catch (error) {
      console.error('❌ Error en handleGuionConversation:', error);
      // Mostrar el error completo para debugging
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error('Error details:', errorMsg);
      
      addMessage(
        '❌ Hubo un error procesando tu respuesta. Por favor, intenta de nuevo.\n\n' +
        `Detalles técnicos: ${errorMsg}`,
        'bot'
      );
      setIsTyping(false);
      setGuionFlow({ active: false });
    }
  };

  const handleCheckoutFlow = async (userMessage: string) => {
    const message = userMessage.trim();

    // Si no hay checkout activo, iniciarlo
    if (!checkoutFlow.active) {
      if (cart.length === 0) {
        addMessage(
          '❌ **Carrito vacío**\n\nTu carrito está vacío. Primero agrega algunos productos antes de finalizar la compra.',
          'bot'
        );
        return;
      }

      setCheckoutFlow({ active: true, step: 'address' });
      addMessage(
        '🛒 **Iniciando proceso de compra**\n\n' +
        `Productos en tu carrito: ${cart.length}\n` +
        `Total: $${cartTotal.toFixed(2)}\n\n` +
        '📍 Por favor, indícame tu **dirección de envío completa**:',
        'bot'
      );
      return;
    }

    // Paso 1: Capturar dirección
    if (checkoutFlow.step === 'address') {
      setCheckoutFlow(prev => ({ 
        ...prev, 
        step: 'confirm',
        shippingAddress: message 
      }));

      addMessage(
        '✅ **Dirección recibida**\n\n' +
        `📍 ${message}\n\n` +
        '📝 Opcionalmente, puedes darme:\n' +
        '- Tu nombre completo\n' +
        '- Tu teléfono\n' +
        '- Tu email\n\n' +
        'O escribe **"confirmar"** para proceder con el pedido.',
        'bot'
      );
      return;
    }

    // Paso 2: Capturar datos adicionales o confirmar
    if (checkoutFlow.step === 'confirm') {
      if (message.toLowerCase() === 'confirmar') {
        // Procesar la orden
        await processOrder();
      } else {
        // Intentar extraer nombre, teléfono, email del mensaje
        const emailMatch = message.match(/[\w.-]+@[\w.-]+\.\w+/);
        const phoneMatch = message.match(/[\d\s\-()]{7,}/);
        
        setCheckoutFlow(prev => ({
          ...prev,
          contactEmail: emailMatch ? emailMatch[0] : prev.contactEmail,
          contactPhone: phoneMatch ? phoneMatch[0] : prev.contactPhone,
          contactName: !emailMatch && !phoneMatch ? message : prev.contactName
        }));

        addMessage(
          '✅ **Información actualizada**\n\n' +
          'Escribe **"confirmar"** para finalizar el pedido o continúa agregando información.',
          'bot'
        );
      }
      return;
    }
  };

  const processOrder = async () => {
    if (!checkoutFlow.shippingAddress) {
      addMessage('❌ Error: No se capturó la dirección de envío', 'bot');
      return;
    }

    setCheckoutFlow(prev => ({ ...prev, step: 'processing' }));
    addMessage('⏳ **Procesando tu orden...**', 'bot');

    const sessionId = chatService.getSessionId();
    
    const result = await createOrderFromCart(
      cart,
      {
        address: checkoutFlow.shippingAddress,
        contact_name: checkoutFlow.contactName,
        contact_phone: checkoutFlow.contactPhone,
        contact_email: checkoutFlow.contactEmail
      },
      sessionId
    );

    // Resetear checkout flow
    setCheckoutFlow({ active: false, step: null });

    if (result.success && result.order_id) {
      addMessage(
        `✅ **¡Orden creada exitosamente!**\n\n` +
        `📋 **Número de orden:** #${result.order_id.substring(0, 8)}\n` +
        `💰 **Total:** $${result.order_total?.toFixed(2)}\n` +
        `📦 **Productos:** ${result.item_count}\n\n` +
        `📍 **Envío a:** ${checkoutFlow.shippingAddress}\n\n` +
        `Puedes ver los detalles de tu orden haciendo clic en el botón de abajo.`,
        'bot',
        {
          type: 'order_created',
          order_id: result.order_id,
          order_total: result.order_total
        }
      );

      // Limpiar carrito
      setCart([]);
      setShowCart(false);

      // Ofrecer ver la orden
      setTimeout(() => {
        if (window.confirm('¿Quieres ver los detalles de tu orden ahora?')) {
          navigate(`/ordenes/${result.order_id}`);
        }
      }, 1000);
    } else {
      addMessage(
        `❌ **Error al crear la orden**\n\n` +
        `${result.message}\n\n` +
        `**Código de error:** ${result.error_code}\n\n` +
        `Por favor, intenta de nuevo o contacta a soporte.`,
        'bot',
        { type: 'error' }
      );
    }
  };

  const handleSendMessage = async (messageText?: string) => {
    const text = (messageText || inputMessage).trim();
    if (!text) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date(),
      status: 'sending'
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    // Actualizar estado a "sent"
    setTimeout(() => {
      setMessages(prev =>
        prev.map(msg =>
          msg.id === userMessage.id ? { ...msg, status: 'sent' } : msg
        )
      );
    }, 300);

    // 🆕 FLUJO DE GUION: Si hay guion activo, continuar conversación
    if (guionFlow.active) {
      setIsTyping(false);
      await handleGuionConversation(text);
      return;
    }

    // Detectar intención de checkout
    const isCheckoutIntent = detectCheckoutIntent(text);
    
    // Si hay checkout activo o se detectó intención de compra
    if (checkoutFlow.active || (isCheckoutIntent && cart.length > 0)) {
      setIsTyping(false);
      await handleCheckoutFlow(text);
      return;
    }

    // 🆕 DETECTAR PRODUCTOS Y USAR GUION SERVICE
    const detectedProducts = detectProductMentions(text);
    
    // Si detecta productos, usar flujo de guion (sin requerir palabras de comparación)
    if (detectedProducts.length > 0) {
      console.log(`🎯 Detectados ${detectedProducts.length} productos → Activando flujo de guion`);
      setIsTyping(false);
      await handleGuionFlow(text, detectedProducts);
      return;
    }

    try {
      // Llamar al servicio de chat
      const response: SemanticSearchResult = await chatService.sendMessage(text);

      // Obtener documentos RAG si está habilitado
      let ragDocs: RAGDoc[] = [];
      if (showRagDocs) {
        try {
          ragDocs = await ragService.searchDocs(text, 3);
        } catch (err) {
          console.warn('No se pudieron obtener docs RAG:', err);
        }
      }

      // Simular tiempo de "escritura" más realista
      const typingDelay = Math.min(response.answer.length * 10, 2000);

      setTimeout(() => {
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: response.answer || 'Lo siento, no obtuve respuesta.',
          sender: 'bot',
          timestamp: new Date(),
          error: response.error,
          ragDocs: ragDocs.length > 0 ? ragDocs : undefined,
          status: 'sent',
          audioUrl: response.audioUrl
        };

        setMessages(prev => [...prev, botMessage]);
        setIsTyping(false);

        // Detectar actualizaciones del carrito en la respuesta
        detectCartUpdates(response.answer, response);
      }, typingDelay);

    } catch (err) {
      console.error('Error enviando mensaje:', err);

      setTimeout(() => {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: '❌ **Error de conexión**\n\nLo siento, hubo un problema conectando con el servidor. Por favor, intenta de nuevo.',
          sender: 'bot',
          timestamp: new Date(),
          error: 'connection_error',
          status: 'error'
        };

        setMessages(prev => [...prev, errorMessage]);
        setIsTyping(false);
      }, 500);
    }
  };

  const handleQuickAction = async (action: QuickAction) => {
    // Acción especial: Ver productos (consume endpoint directamente)
    if (action.message === 'list_products_action') {
      setIsTyping(true);

      try {
        // Importar productService
        const { productService } = await import('../services/graphqlservices');

        // Llamar al endpoint listProducts
        const products = await productService.listProducts(20);

        if (!products || products.length === 0) {
          addMessage(
            '❌ **No hay productos disponibles**\n\nNo se encontraron productos en el inventario.',
            'bot'
          );
          setIsTyping(false);
          return;
        }

        // Formatear la lista de productos
        let mensaje = `📦 **Productos Disponibles** (${products.length})\n\n`;

        products.forEach((product, index) => {
          const stockIcon = product.quantityAvailable > 10 ? '✅' : product.quantityAvailable > 0 ? '⚠️' : '❌';
          mensaje += `${index + 1}. **${product.productName}**\n`;
          mensaje += `   💰 Precio: $${product.unitCost}\n`;
          mensaje += `   ${stockIcon} Stock: ${product.quantityAvailable} unidades\n`;
          mensaje += `   📍 Ubicación: ${product.warehouseLocation}\n`;
          if (product.shelfLocation) {
            mensaje += `   🗄️ Estante: ${product.shelfLocation}\n`;
          }
          mensaje += '\n';
        });

        mensaje += '¿Te interesa alguno de estos productos? ¡Pregúntame sobre ellos!';

        addMessage(mensaje, 'bot');
        setIsTyping(false);

      } catch (error) {
        console.error('Error al cargar productos:', error);
        addMessage(
          '❌ **Error al cargar productos**\n\nHubo un problema al consultar el inventario. Por favor, intenta de nuevo.',
          'bot'
        );
        setIsTyping(false);
      }
    } else {
      // Otras acciones (si las agregas en el futuro)
      handleSendMessage(action.message);
    }
  };

  const removeFromCart = (productId: string) => {
    setCart(prev => prev.filter(item => item.product_id !== productId));
    addMessage(`✅ Producto removido del carrito`, 'bot');
  };

  const clearCart = () => {
    if (window.confirm('¿Seguro que quieres vaciar el carrito?')) {
      setCart([]);
      addMessage(`🗑️ Carrito vaciado`, 'bot');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const toggleChat = () => {
    setIsOpen(o => !o);
  };

  const handleNewConversation = () => {
    chatService.resetSession();
    guionService.resetSession();
    setMessages([
      {
        id: Date.now().toString(),
        text: '🔄 **Nueva conversación iniciada**\n\n¡Hola de nuevo! Estoy listo para ayudarte. ¿En qué puedo asistirte?',
        sender: 'bot',
        timestamp: new Date(),
        status: 'sent'
      }
    ]);
    setCheckoutFlow({ active: false, step: null });
    setGuionFlow({ active: false });
    setHistoryLoaded(false);  // Resetear para permitir cargar historial de nueva sesión
    resetOrderState();
  };

  const getErrorIcon = (error: string | null | undefined) => {
    if (!error) return null;

    const errorMessages: Record<string, string> = {
      'timeout': 'La respuesta tardó mucho tiempo',
      'service_unavailable': 'Servicio temporalmente no disponible',
      'internal_error': 'Error interno del servidor',
      'connection_error': 'Error de conexión',
      'graphql_error': 'Error en la consulta'
    };

    return (
      <div className="message-error" title={errorMessages[error] || 'Error'}>
        <FiAlertCircle size={14} />
        <span>{errorMessages[error] || 'Error'}</span>
      </div>
    );
  };

  const getMessageStatusIcon = (status?: 'sending' | 'sent' | 'error') => {
    switch (status) {
      case 'sending':
        return <FiClock size={12} style={{ opacity: 0.5 }} />;
      case 'sent':
        return <FiCheck size={12} style={{ opacity: 0.6 }} />;
      case 'error':
        return <FiAlertCircle size={12} style={{ color: 'var(--error)' }} />;
      default:
        return null;
    }
  };

  return (
    <>
      {/* Toggle Button */}
      <button
        className={`chat-toggle-btn ${isOpen ? 'open' : ''}`}
        onClick={toggleChat}
        aria-label={isOpen ? 'Cerrar chat' : 'Abrir chat'}
      >
        {isOpen ? (
          <FiX size={32} />
        ) : (
          <>
            <FiMessageCircle size={32} />
            {unreadCount > 0 && (
              <span className="chat-badge">{unreadCount}</span>
            )}
            {cart.length > 0 && (
              <span className="cart-badge-toggle">{cart.length}</span>
            )}
          </>
        )}
      </button>

      {/* Chat Window */}
      <div className={`chat-window ${isOpen ? 'open' : ''}`}>
        {/* Header */}
        <div className="chat-header">
          <div className="chat-header-info">
            <div className={`bot-avatar ${isTyping ? 'typing' : ''}`}>
              🤖
            </div>
            <div>
              <h3>Alex - Asistente de Ventas</h3>
              <p className="status">
                <span className="status-dot"></span>
                {isTyping ? 'Escribiendo...' : checkoutFlow.active ? 'Procesando compra...' : 'En línea'}
              </p>
            </div>
          </div>

          <div className="chat-header-actions">
            {cart.length > 0 && (
              <button
                className={`icon-button cart-button ${showCart ? 'active' : ''}`}
                onClick={() => setShowCart(!showCart)}
                title="Ver carrito"
              >
                <FiShoppingCart size={18} />
                <span className="cart-count">{cart.length}</span>
              </button>
            )}
            <button
              className={`icon-button ${showRagDocs ? 'active' : ''}`}
              onClick={() => setShowRagDocs(!showRagDocs)}
              title={showRagDocs ? 'Ocultar docs RAG' : 'Mostrar docs RAG'}
              aria-label="Toggle RAG docs"
            >
              📄
            </button>
            <button
              className="icon-button"
              onClick={handleNewConversation}
              title="Nueva conversación"
              aria-label="Nueva conversación"
            >
              🔄
            </button>
            <button
              className="close-chat-btn"
              onClick={toggleChat}
              aria-label="Cerrar chat"
            >
              ✖️
            </button>
          </div>
        </div>

        {/* Cart Sidebar */}
        {showCart && cart.length > 0 && (
          <div className="cart-sidebar">
            <div className="cart-sidebar-header">
              <h4>🛒 Tu Carrito</h4>
              <button onClick={() => setShowCart(false)} className="close-cart">
                <FiX size={16} />
              </button>
            </div>
            <div className="cart-items">
              {cart.map(item => (
                <div key={item.product_id} className="cart-item">
                  <div className="cart-item-info">
                    <div className="cart-item-name">{item.product_name}</div>
                    <div className="cart-item-details">
                      Cantidad: {item.quantity} × ${item.unit_price.toFixed(2)}
                    </div>
                  </div>
                  <div className="cart-item-actions">
                    <div className="cart-item-price">
                      ${(item.unit_price * item.quantity).toFixed(2)}
                    </div>
                    <button
                      onClick={() => removeFromCart(item.product_id)}
                      className="remove-item"
                      title="Eliminar"
                    >
                      <FiTrash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="cart-footer">
              <div className="cart-total">
                <strong>Total:</strong>
                <strong>${cartTotal.toFixed(2)}</strong>
              </div>
              <button
                onClick={() => handleQuickAction({ id: 'checkout', label: '💳 Finalizar compra', message: 'Quiero finalizar mi compra' })}
                className="checkout-btn"
                disabled={isCreating}
              >
                <FiPackage size={16} />
                {isCreating ? 'Procesando...' : 'Finalizar Compra'}
              </button>
              <button onClick={clearCart} className="clear-cart-btn">
                Vaciar Carrito
              </button>
            </div>
          </div>
        )}

        {/* Messages */}
        <div
          className="chat-messages"
          ref={chatMessagesRef}
          role="log"
          aria-live="polite"
        >
          {isLoadingHistory && (
            <div className="loading-history">
              <div className="loading-spinner"></div>
              <p>Cargando historial...</p>
            </div>
          )}
          {messages.map((message, index) => (
            <div key={message.id}>
              {/* Message Bubble */}
              <div
                className={`message ${message.sender === 'user' ? 'user-message' : 'bot-message'}`}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className="message-content">
                  {message.sender === 'bot' ? (
                    <ReactMarkdown
                      components={{
                        p: ({ node, ...props }) => <p {...props} />,
                        strong: ({ node, ...props }) => <strong {...props} />,
                        em: ({ node, ...props }) => <em {...props} />,
                        code({ node, className, children, ...props }: any) {
                          const match = /language-(\w+)/.exec(className || '');
                          return match ? (
                            <pre className="code-block">
                              <code className={className} {...props}>{children}</code>
                            </pre>
                          ) : (
                            <code className="code-inline" {...props}>{children}</code>
                          );
                        },
                        ul: ({ node, ...props }) => <ul {...props} />,
                        ol: ({ node, ...props }) => <ol {...props} />,
                        li: ({ node, ...props }) => <li {...props} />,
                        h1: ({ node, ...props }) => <h1 {...props} />,
                        h2: ({ node, ...props }) => <h2 {...props} />,
                        h3: ({ node, ...props }) => <h3 {...props} />,
                        a: ({ node, ...props }) => (
                          <a {...props} target="_blank" rel="noopener noreferrer" />
                        ),
                        blockquote: ({ node, ...props }) => <blockquote {...props} />,
                        hr: ({ node, ...props }) => <hr {...props} />
                      }}
                    >
                      {message.text}
                    </ReactMarkdown>
                  ) : (
                    <p>{message.text}</p>
                  )}

                  {/* Reproducir audio si está disponible (solo para bot) */}
                  {message.sender === 'bot' && message.audioUrl && (
                    <AudioPlayer
                      audioUrl={message.audioUrl}
                      autoPlay={true}
                      onError={(err) => console.error('Error reproduciendo audio:', err)}
                    />
                  )}

                  {/* Botón especial para ver orden creada */}
                  {message.metadata?.type === 'order_created' && message.metadata?.order_id && (
                    <button
                      className="view-order-button"
                      onClick={() => navigate(`/ordenes/${message.metadata?.order_id}`)}
                    >
                      <FiPackage size={16} />
                      Ver mi orden
                    </button>
                  )}

                  <div className="message-footer">
                    <span className="message-time">
                      {message.timestamp.toLocaleTimeString('es-ES', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                    {message.sender === 'user' && getMessageStatusIcon(message.status)}
                    {getErrorIcon(message.error)}
                  </div>
                </div>
              </div>

              {/* RAG Documents Display */}
              {message.ragDocs && message.ragDocs.length > 0 && (
                <div className="rag-docs-container">
                  <div className="rag-docs-header">
                    <FiFileText size={14} />
                    <span>Documentos consultados ({message.ragDocs.length})</span>
                  </div>
                  {message.ragDocs.map((doc, idx) => (
                    <div key={idx} className="rag-doc">
                      <div className="rag-doc-header">
                        <span className="rag-doc-category">{doc.category}</span>
                        <span className="rag-doc-score">
                          {(doc.relevance_score * 100).toFixed(0)}% relevante
                        </span>
                      </div>
                      <p className="rag-doc-content">
                        {doc.content.slice(0, 200)}...
                      </p>
                      <span className="rag-doc-source">
                        Fuente: {doc.source}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Quick Actions - Solo mostrar después del primer mensaje del bot */}
              {index === 0 && message.sender === 'bot' && (
                <div className="quick-actions">
                  {quickActions.map(action => (
                    <button
                      key={action.id}
                      className="quick-action"
                      onClick={() => handleQuickAction(action)}
                      disabled={isTyping}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          {/* Typing Indicator */}
          {(isTyping || isCreating) && (
            <div className="message bot-message">
              <div className="message-content typing">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                {isCreating && <p style={{ fontSize: '0.85em', marginTop: '0.5rem' }}>Creando tu orden...</p>}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="chat-input-container">
          <input
            ref={inputRef}
            type="text"
            placeholder={
              checkoutFlow.step === 'address' 
                ? "Escribe tu dirección de envío..." 
                : checkoutFlow.step === 'confirm'
                ? 'Escribe "confirmar" o agrega más información...'
                : "Escribe tu mensaje..."
            }
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            className="chat-input"
            disabled={isTyping || isCreating}
            aria-label="Mensaje"
            autoComplete="off"
            maxLength={500}
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={!inputMessage.trim() || isTyping || isCreating}
            className="send-button"
            aria-label="Enviar mensaje"
          >
            <FiSend size={22} />
          </button>
        </div>

        {/* Footer */}
        <div className="chat-footer">
          <small>Session: {chatService.getSessionId().slice(-8)}</small>
          {showRagDocs && (
            <small className="rag-mode-indicator"> • Modo RAG activo</small>
          )}
          {cart.length > 0 && (
            <small className="cart-indicator"> • {cart.length} en carrito</small>
          )}
        </div>
      </div>
    </>
  );
};

export default ChatBot;