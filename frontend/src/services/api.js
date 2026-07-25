import axios from 'axios';
import { authService } from './auth';
import { API_BASE_URL, API_URL } from './apiConfig';

export { API_BASE_URL };

const api = axios.create({
  baseURL: API_URL,
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
    const authRoutes = [
      '/users/auth',
      '/users/refresh-token',
      '/users/forgot-password',
      '/users/reset-password'
    ];

    const isAuthRoute = authRoutes.some(route => config.url?.includes(route));

    if (!isAuthRoute) {
      const token = authService.getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptador para tratar respostas e erros (com refresh automático)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest?._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch(err => Promise.reject(err));
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

    if (error.response?.status === 403) {
      // Envelope padrão: a mensagem vem sempre em `message` (não mais `error`).
      console.warn('Acesso negado:', error.response?.data?.message);
    }

    return Promise.reject(error);
  }
);

export default api;