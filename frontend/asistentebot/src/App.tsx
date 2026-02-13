// src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './protected/protectedroute';
import Login from './login/login';
import Store from './store/store';
import ChatBot from './chat/chatbot';
import OrderDetail from './orders/orderdetail';
import Orders from './orders/orders';
import './App.css';

function AppContent() {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  
  // No mostrar ChatBot en la página de login
  const showChatBot = isAuthenticated && location.pathname !== '/login';

  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route 
          path="/tienda" 
          element={
            <ProtectedRoute>
              <Store />
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/store" 
          element={
            <ProtectedRoute>
              <Store />
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/productos" 
          element={
            <ProtectedRoute>
              <Store />
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/ordenes" 
          element={
            <ProtectedRoute>
              <Orders />
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/ordenes/:orderId" 
          element={
            <ProtectedRoute>
              <OrderDetail />
            </ProtectedRoute>
          } 
        />

        <Route path="/" element={<Navigate to="/login" replace />} />

        <Route
          path="*"
          element={
            <div className="loading-screen">
              <h1 style={{ fontSize: '48px', marginBottom: '16px' }}>404</h1>
              <p>Página no encontrada</p>
              <button
                onClick={() => window.location.href = '/tienda'}
                style={{
                  marginTop: '20px',
                  padding: '12px 24px',
                  background: '#1a1a1a',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                Volver a la tienda
              </button>
            </div>
          }
        />
      </Routes>

      {/* ChatBot solo visible cuando está autenticado */}
      {showChatBot && <ChatBot />}
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;
