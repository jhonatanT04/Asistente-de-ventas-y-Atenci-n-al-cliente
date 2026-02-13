// src/services/api.ts
import axios from 'axios';
import type { User, Product, Message, LoginResponse, LoginCredentials } from '../types/types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar el token a cada petición
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para manejar respuestas y errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expirado o inválido
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (identifier: string, password: string): Promise<LoginResponse> => {
    // Detectar si es email o username
    const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(identifier);
    
    const credentials: LoginCredentials = {
      ...(isEmail ? { email: identifier } : { username: identifier }),
      password
    };
    
    console.log('🔐 Intentando login con:', isEmail ? 'email' : 'username', identifier);
    
    const response = await api.post<LoginResponse>('/auth/login', credentials);
    
    // Guardar token
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      console.log('✅ Token guardado correctamente');
    }
    
    return response.data;
  },
  
  register: async (username: string, email: string, password: string) => {
    const response = await api.post('/auth/register', { username, email, password });
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },

  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('access_token');
  },

  getToken: (): string | null => {
    return localStorage.getItem('access_token');
  },

  getUserFromToken: (): User | null => {
    const token = authAPI.getToken();
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
      
      // El payload contiene: id, username, email, role
      return {
        id: payload.id,
        username: payload.username,
        email: payload.email,
        role: payload.role
      };
    } catch (error) {
      console.error('Error decodificando token:', error);
      return null;
    }
  },
};

// Products API
export const productsAPI = {
  getAll: async (): Promise<Product[]> => {
    const response = await api.get('/products');
    return response.data;
  },
  
  getById: async (id: string): Promise<Product> => {
    const response = await api.get(`/products/${id}`);
    return response.data;
  },
  
  getByCategory: async (category: string): Promise<Product[]> => {
    const response = await api.get(`/products/category/${category}`);
    return response.data;
  },
};

// Chat API
export const chatAPI = {
  sendMessage: async (message: string): Promise<Message> => {
    const response = await api.post('/chat', { message });
    return response.data;
  },
};

export default api;