// Login.tsx - BRUTAL MINIMALIST DESIGN con mejor UX
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './login.css';

interface ValidationState {
  identifier: 'valid' | 'invalid' | 'neutral';
  password: 'valid' | 'invalid' | 'neutral';
}

const Login: React.FC = () => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [validation, setValidation] = useState<ValidationState>({
    identifier: 'neutral',
    password: 'neutral'
  });
  
  const navigate = useNavigate();
  const { login } = useAuth();

  // Validación en tiempo real
  useEffect(() => {
    if (identifier.length === 0) {
      setValidation(prev => ({ ...prev, identifier: 'neutral' }));
    } else if (identifier.length >= 3) {
      // Validar si es email o username válido
      const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(identifier);
      const isUsername = /^[a-zA-Z0-9_]{3,}$/.test(identifier);
      setValidation(prev => ({ 
        ...prev, 
        identifier: (isEmail || isUsername) ? 'valid' : 'invalid' 
      }));
    } else {
      setValidation(prev => ({ ...prev, identifier: 'invalid' }));
    }
  }, [identifier]);

  useEffect(() => {
    if (password.length === 0) {
      setValidation(prev => ({ ...prev, password: 'neutral' }));
    } else if (password.length >= 6) {
      setValidation(prev => ({ ...prev, password: 'valid' }));
    } else {
      setValidation(prev => ({ ...prev, password: 'invalid' }));
    }
  }, [password]);

  // Limpiar error cuando el usuario empieza a escribir
  useEffect(() => {
    if (error && (identifier || password)) {
      setError('');
    }
  }, [identifier, password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    // Validación básica
    if (!identifier || !password) {
      setError('⚠ Por favor completa todos los campos');
      return;
    }

    if (validation.identifier === 'invalid') {
      setError('⚠ El usuario/email ingresado no es válido');
      return;
    }

    if (validation.password === 'invalid') {
      setError('⚠ La contraseña debe tener al menos 6 caracteres');
      return;
    }

    try {
      setIsLoading(true);
      await login(identifier, password);
      
      // Redirigir a la tienda después del login exitoso
      navigate('/tienda');
    } catch (err: any) {
      console.error('Error de login:', err);
      
      // Manejo de errores específicos según el código de estado
      if (err.response) {
        switch (err.response.status) {
          case 401:
            setError('🔒 Credenciales inválidas. Verifica tu usuario/email y contraseña.');
            break;
          case 403:
            setError('⛔ Usuario desactivado. Contacta al administrador.');
            break;
          case 429:
            setError('⏱ Demasiados intentos. Por favor espera un momento e intenta de nuevo.');
            break;
          case 400:
            setError(err.response.data?.detail || '⚠ Datos inválidos. Verifica la información ingresada.');
            break;
          case 500:
            setError('🔧 Error del servidor. Por favor intenta más tarde.');
            break;
          default:
            setError('❌ Error al iniciar sesión. Por favor intenta de nuevo.');
        }
      } else if (err.request) {
        setError('🌐 No se pudo conectar con el servidor. Verifica tu conexión a internet.');
      } else {
        setError('❌ Error inesperado. Por favor intenta de nuevo.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    // Permitir envío con Enter si no está cargando
    if (e.key === 'Enter' && !isLoading) {
      handleSubmit(e as any);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Bienvenido</h1>
          <p>Inicia sesión para continuar</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form" noValidate>
          {/* Campo de Usuario/Email */}
          <div className={`form-group ${validation.identifier}`}>
            <label htmlFor="identifier">
              Usuario o Email
            </label>
            <input
              type="text"
              id="identifier"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value.trim())}
              onKeyPress={handleKeyPress}
              placeholder="usuario o tu@email.com"
              disabled={isLoading}
              autoComplete="username"
              autoFocus
              required
              aria-label="Usuario o Email"
              aria-invalid={validation.identifier === 'invalid'}
            />
          </div>

          {/* Campo de Contraseña */}
          <div className={`form-group ${validation.password}`}>
            <label htmlFor="password">
              Contraseña
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="••••••••"
                disabled={isLoading}
                autoComplete="current-password"
                required
                aria-label="Contraseña"
                aria-invalid={validation.password === 'invalid'}
              />
              <button
                type="button"
                className="show-password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                tabIndex={-1}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          {/* Mensaje de Error */}
          {error && (
            <div 
              className="error-message" 
              role="alert"
              aria-live="polite"
            >
              {error}
            </div>
          )}

          {/* Botón de Submit */}
          <button 
            type="submit" 
            className={`login-button ${isLoading ? 'loading' : ''}`}
            disabled={isLoading || validation.identifier === 'invalid' || validation.password === 'invalid'}
            aria-busy={isLoading}
          >
            {isLoading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
          </button>
        </form>

        {/* Footer */}
        <div className="login-footer">
          <a 
            href="/forgot-password" 
            className="forgot-password"
            tabIndex={isLoading ? -1 : 0}
          >
            ¿Olvidaste tu contraseña?
          </a>
        </div>

        {/* Divider y Link de Registro (Opcional) */}
        {/* 
        <div className="login-divider">
          <span>O</span>
        </div>
        <a href="/register" className="register-link">
          Crear nueva cuenta
        </a>
        */}
      </div>
    </div>
  );
};

export default Login;