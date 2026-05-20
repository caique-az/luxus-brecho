import axios from 'axios';
import { authService } from './auth';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Flag para evitar múltiplas tentativas de refresh simultâneas
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Interceptador para adicionar token de autenticação
api.interceptors.request.use(
  async (config) => {
    // Não adiciona token em rotas públicas
    const publicRoutes = ['/users/auth', '/users', '/products', '/categories', '/health'];
    const isPublicRoute = publicRoutes.some(route => 
      config.url?.includes(route) && config.method?.toLowerCase() === 'get'
    );
    
    // Rotas de autenticação não precisam de token
    const authRoutes = ['/users/auth', '/users/refresh-token', '/users/forgot-password', '/users/reset-password'];
    const isAuthRoute = authRoutes.some(route => config.url?.includes(route));
    
if (!isAuthRoute) {
  const token = authService.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
}
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptador para tratar respostas e erros (com refresh automático)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Se o erro for 401 e não for uma tentativa de retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Se já está fazendo refresh, adiciona à fila
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const result = await authService.refreshAccessToken();
        
        if (result.success) {
          const newToken = authService.getAccessToken();
          processQueue(null, newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        } else {
          processQueue(new Error('Refresh failed'), null);
          // Token inválido - faz logout
          authService.logout();
          window.location.href = '/login';
          return Promise.reject(error);
        }
      } catch (refreshError) {
        processQueue(refreshError, null);
        authService.logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    
    // Se for 403 (Forbidden), não tenta refresh
    if (error.response?.status === 403) {
      console.warn('Acesso negado:', error.response?.data?.error);
    }
    
    return Promise.reject(error);
  }
);

export default api;