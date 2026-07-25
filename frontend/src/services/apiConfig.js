/**
 * Fonte única da URL da API no frontend.
 *
 * Em desenvolvimento a base é derivada do host que serviu a página: abrir o
 * Vite em http://192.168.0.3:5173 faz a API apontar para
 * http://192.168.0.3:5000, então testar de outro dispositivo da mesma rede
 * não exige arquivo gerado nem VITE_API_URL ajustado à mão.
 *
 * VITE_API_URL continua sendo o override explícito (obrigatório em produção).
 */

const API_PORT = import.meta.env.VITE_API_PORT || '5000';

// Aceita a env var com ou sem o sufixo /api para evitar bases duplicadas
const normalizeBase = (url) => url.trim().replace(/\/+$/, '').replace(/\/api$/, '');

const deriveDevBase = () => {
  if (typeof window === 'undefined') return `http://127.0.0.1:${API_PORT}`;
  return `http://${window.location.hostname}:${API_PORT}`;
};

const rawBase =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? deriveDevBase() : `http://127.0.0.1:${API_PORT}`);

/** Base sem sufixo: http://host:5000 */
export const API_BASE_URL = normalizeBase(rawBase);

/** Base das rotas do backend: http://host:5000/api */
export const API_URL = `${API_BASE_URL}/api`;
