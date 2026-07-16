const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

// Chaves do localStorage
const STORAGE_KEYS = {
  USER: 'luxus_user',
  AUTH: 'luxus_auth',
  ACCESS_TOKEN: 'luxus_access_token',
  REFRESH_TOKEN: 'luxus_refresh_token',
  TOKEN_EXPIRES: 'luxus_token_expires',
};

export const authService = {
  /**
   * Obtém o token de acesso atual
   */
  getAccessToken() {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  },

  /**
   * Obtém o refresh token atual
   */
  getRefreshToken() {
    return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
  },

  /**
   * Verifica se o token está expirado
   */
  isTokenExpired() {
    const expires = localStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRES);
    if (!expires) return true;
    return Date.now() > parseInt(expires, 10);
  },

  /**
   * Salva os tokens no localStorage
   */
  saveTokens(accessToken, refreshToken, expiresIn) {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    // Calcula quando o token expira (com margem de 5 minutos)
    const expiresAt = Date.now() + (expiresIn * 1000) - (5 * 60 * 1000);
    localStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRES, expiresAt.toString());
  },

  /**
   * Remove os tokens do localStorage
   */
  clearTokens() {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.TOKEN_EXPIRES);
  },

  /**
   * Renova o token de acesso usando o refresh token
   */
  async refreshAccessToken() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      return { success: false, error: 'Refresh token não encontrado' };
    }

    try {
      const response = await fetch(`${API_URL}/users/refresh-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      const data = await response.json();

      if (!response.ok) {
        this.clearTokens();
        return { success: false, error: data.message || 'Erro ao renovar token' };
      }

      this.saveTokens(data.access_token, data.refresh_token, data.expires_in);
      return { success: true };
    } catch (error) {
      console.error('Erro ao renovar token:', error);
      this.clearTokens();
      return { success: false, error: 'Erro ao renovar token' };
    }
  },

  /**
   * Obtém um token válido (renova se necessário)
   */
  async getValidToken() {
    if (!this.isTokenExpired()) {
      return this.getAccessToken();
    }

    const result = await this.refreshAccessToken();
    if (result.success) {
      return this.getAccessToken();
    }

    return null;
  },

  /**
   * Faz login do usuário
   */
  async login(credentials) {
    try {
      const response = await fetch(`${API_URL}/users/auth`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      const data = await response.json();

      // Verifica se o email não foi confirmado
      if (response.status === 403 && data.email_not_confirmed) {
        return { 
          success: false, 
          error: data.message || 'Email não confirmado',
          emailNotConfirmed: true 
        };
      }

      if (!response.ok) {
        return { success: false, error: data.message || 'Credenciais inválidas' };
      }

      if (data && data.user) {
        // Salvar dados do usuário no localStorage
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user));
        localStorage.setItem(STORAGE_KEYS.AUTH, 'authenticated');
        
        // Salvar tokens JWT
        if (data.access_token && data.refresh_token) {
          this.saveTokens(data.access_token, data.refresh_token, data.expires_in || 86400);
        }
        
        return { success: true, user: data.user };
      }

      return { success: false, error: 'Credenciais inválidas' };
    } catch (error) {
      console.error('Erro no login:', error);
      return { success: false, error: 'Erro ao fazer login. Tente novamente.' };
    }
  },

  /**
   * Registra novo usuário
   */
  async register(data) {
    try {
      // Validar se as senhas coincidem
      if (data.senha !== data.confirmarSenha) {
        return { success: false, error: 'As senhas não coincidem' };
      }

      // Criar payload para o backend
      const payload = {
        nome: data.nome,
        email: data.email,
        senha: data.senha,
        tipo: 'Cliente', // Sempre cliente para registro via frontend
      };

      const response = await fetch(`${API_URL}/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const responseData = await response.json();

      if (!response.ok) {
        return { 
          success: false, 
          error: responseData.message || 'Erro ao criar conta' 
        };
      }

      if (responseData && responseData.user) {
        // Retorna sucesso mas indica que precisa confirmar email
        return { 
          success: true, 
          user: responseData.user,
          requiresEmailConfirmation: responseData.email_confirmation_required || false
        };
      }

      return { success: false, error: 'Erro ao criar conta' };
    } catch (error) {
      console.error('Erro no registro:', error);
      return { success: false, error: 'Erro ao criar conta. Tente novamente.' };
    }
  },

  /**
   * Reenvia email de confirmação
   */
  async resendConfirmationEmail(email) {
    try {
      const response = await fetch(`${API_URL}/users/resend-confirmation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        return { success: false, error: data.message || 'Erro ao reenviar email' };
      }

      return { success: true };
    } catch (error) {
      console.error('Erro ao reenviar email:', error);
      return { success: false, error: 'Erro ao reenviar email. Tente novamente.' };
    }
  },

  /**
   * Faz logout do usuário
   */
  logout() {
    try {
      localStorage.removeItem(STORAGE_KEYS.AUTH);
      localStorage.removeItem(STORAGE_KEYS.USER);
      this.clearTokens();
    } catch (error) {
      console.error('Erro no logout:', error);
    }
  },

  /**
   * Verifica se o usuário está autenticado
   */
  isAuthenticated() {
    try {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH);
      const accessToken = this.getAccessToken();
      return token !== null && accessToken !== null;
    } catch (error) {
      console.error('Erro ao verificar autenticação:', error);
      return false;
    }
  },

  /**
   * Obtém dados do usuário atual
   */
  getCurrentUser() {
    try {
      const userData = localStorage.getItem(STORAGE_KEYS.USER);
      if (userData) {
        return JSON.parse(userData);
      }
      return null;
    } catch (error) {
      console.error('Erro ao obter usuário atual:', error);
      return null;
    }
  },

  /**
   * Inicializa o serviço de autenticação
   */
  initialize() {
    try {
      const isAuth = this.isAuthenticated();
      if (isAuth) {
        return this.getCurrentUser();
      }
      return null;
    } catch (error) {
      console.error('Erro ao inicializar auth service:', error);
      return null;
    }
  },

  /**
   * Atualiza dados do usuário no storage
   */
  updateUserData(user) {
    try {
      localStorage.setItem('luxus_user', JSON.stringify(user));
    } catch (error) {
      console.error('Erro ao atualizar dados do usuário:', error);
    }
  },

  /**
   * Solicita exclusão de conta - envia código por email
   */
  async requestAccountDeletion(userId) {
    try {
      const token = this.getAccessToken();
      const response = await fetch(`${API_URL}/users/request-deletion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ user_id: userId }),
      });

      const data = await response.json();

      if (!response.ok) {
        return { success: false, error: data.message || 'Erro ao solicitar exclusão' };
      }

      return { success: true };
    } catch (error) {
      console.error('Erro ao solicitar exclusão de conta:', error);
      return { success: false, error: 'Erro ao solicitar exclusão. Tente novamente.' };
    }
  },

  /**
   * Confirma exclusão de conta com código de 6 dígitos
   */
  async confirmAccountDeletion(userId, code) {
    try {
      const token = this.getAccessToken();
      const response = await fetch(`${API_URL}/users/confirm-deletion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ user_id: userId, code }),
      });

      const data = await response.json();

      if (!response.ok) {
        return { success: false, error: data.message || 'Erro ao confirmar exclusão' };
      }

      // Limpa dados locais após exclusão
      this.logout();

      return { success: true };
    } catch (error) {
      console.error('Erro ao confirmar exclusão de conta:', error);
      return { success: false, error: 'Erro ao confirmar exclusão. Tente novamente.' };
    }
  },
};
