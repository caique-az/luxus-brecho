import AsyncStorage from '@react-native-async-storage/async-storage';
import { getApiUrl } from '../utils/networkUtils';

export interface User {
  id: number;
  nome: string;
  email: string;
  tipo: 'Cliente' | 'Administrador';
  ativo: boolean;
  email_confirmado: boolean;
  data_criacao: string;
  data_atualizacao: string;
}

export interface LoginCredentials {
  email: string;
  senha: string;
}

export interface RegisterData {
  nome: string;
  email: string;
  senha: string;
  confirmarSenha: string;
}

export interface AuthResponse {
  message: string;
  user: User;
}

const AUTH_TOKEN_KEY = '@luxus_brecho:auth_token'; // legado (só removido no logout)
const ACCESS_TOKEN_KEY = '@luxus_brecho:access_token';
const REFRESH_TOKEN_KEY = '@luxus_brecho:refresh_token';
const USER_DATA_KEY = '@luxus_brecho:user_data';

class AuthService {
  private currentUser: User | null = null;

  /**
   * Faz login do usuário
   */
  async login(credentials: LoginCredentials): Promise<{ success: boolean; user?: User; error?: string; emailNotConfirmed?: boolean }> {
    try {
      const response = await fetch(`${getApiUrl()}/users/auth`, {
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
        // Salvar dados do usuário e os tokens JWT reais devolvidos pelo backend
        await AsyncStorage.setItem(USER_DATA_KEY, JSON.stringify(data.user));
        if (data.access_token) {
          await AsyncStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
        }
        if (data.refresh_token) {
          await AsyncStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
        }

        this.currentUser = data.user;

        return { success: true, user: data.user };
      }

      return { success: false, error: 'Credenciais inválidas' };
    } catch (error) {
      console.error('Erro no login:', error);
      return { success: false, error: 'Erro ao fazer login. Tente novamente.' };
    }
  }

  /**
   * Registra novo usuário
   */
  async register(data: RegisterData): Promise<{ success: boolean; user?: User; error?: string; requiresEmailConfirmation?: boolean }> {
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
        tipo: 'Cliente' as const, // Sempre cliente para registro via mobile
      };

      const response = await fetch(`${getApiUrl()}/users`, {
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
    } catch (error: any) {
      console.error('Erro no registro:', error);
      return { success: false, error: 'Erro ao criar conta. Tente novamente.' };
    }
  }

  /**
   * Reenvia email de confirmação
   */
  async resendConfirmationEmail(email: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await fetch(`${getApiUrl()}/users/resend-confirmation`, {
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
  }

  /**
   * Faz logout do usuário
   */
  async logout(): Promise<void> {
    try {
      await AsyncStorage.multiRemove([
        AUTH_TOKEN_KEY,
        ACCESS_TOKEN_KEY,
        REFRESH_TOKEN_KEY,
        USER_DATA_KEY,
      ]);
      this.currentUser = null;
    } catch (error) {
      console.error('Erro no logout:', error);
    }
  }

  /**
   * Verifica se o usuário está autenticado (há sessão salva).
   * Baseia-se nos dados do usuário para não deslogar sessões legadas que
   * ainda não possuem o token JWT armazenado.
   */
  async isAuthenticated(): Promise<boolean> {
    try {
      const userData = await AsyncStorage.getItem(USER_DATA_KEY);
      return userData !== null;
    } catch (error) {
      console.error('Erro ao verificar autenticação:', error);
      return false;
    }
  }

  /**
   * Retorna o access token JWT armazenado (ou null).
   */
  async getAccessToken(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
    } catch (error) {
      console.error('Erro ao obter access token:', error);
      return null;
    }
  }

  /**
   * Monta o header Authorization com o Bearer token, se houver.
   * Retorna objeto vazio quando não há token (sessão legada / não logado).
   */
  async getAuthHeaders(): Promise<Record<string, string>> {
    const token = await this.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /**
   * Renova o access token usando o refresh token armazenado.
   * Retorna o novo access token, ou null se não for possível renovar.
   */
  async refreshAccessToken(): Promise<string | null> {
    try {
      const refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
      if (!refreshToken) {
        return null;
      }

      const response = await fetch(`${getApiUrl()}/users/refresh-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        return null;
      }

      const data = await response.json();
      if (data?.access_token) {
        await AsyncStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
        if (data.refresh_token) {
          await AsyncStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
        }
        return data.access_token;
      }
      return null;
    } catch (error) {
      console.error('Erro ao renovar token:', error);
      return null;
    }
  }

  /**
   * Obtém dados do usuário atual
   */
  async getCurrentUser(): Promise<User | null> {
    try {
      if (this.currentUser) {
        return this.currentUser;
      }

      const userData = await AsyncStorage.getItem(USER_DATA_KEY);
      if (userData) {
        this.currentUser = JSON.parse(userData);
        return this.currentUser;
      }

      return null;
    } catch (error) {
      console.error('Erro ao obter usuário atual:', error);
      return null;
    }
  }

  /**
   * Inicializa o serviço de autenticação
   */
  async initialize(): Promise<User | null> {
    try {
      const isAuth = await this.isAuthenticated();
      if (isAuth) {
        return await this.getCurrentUser();
      }
      return null;
    } catch (error) {
      console.error('Erro ao inicializar auth service:', error);
      return null;
    }
  }

  /**
   * Atualiza dados do usuário no storage
   */
  async updateUserData(user: User): Promise<void> {
    try {
      await AsyncStorage.setItem(USER_DATA_KEY, JSON.stringify(user));
      this.currentUser = user;
    } catch (error) {
      console.error('Erro ao atualizar dados do usuário:', error);
    }
  }

  /**
   * Solicita exclusão de conta - envia código por email
   */
  async requestAccountDeletion(userId: number): Promise<{ success: boolean; error?: string }> {
    try {
      const authHeaders = await this.getAuthHeaders();
      const response = await fetch(`${getApiUrl()}/users/request-deletion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
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
  }

  /**
   * Confirma exclusão de conta com código de 6 dígitos
   */
  async confirmAccountDeletion(userId: number, code: string): Promise<{ success: boolean; error?: string }> {
    try {
      const authHeaders = await this.getAuthHeaders();
      const response = await fetch(`${getApiUrl()}/users/confirm-deletion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({ user_id: userId, code }),
      });

      const data = await response.json();

      if (!response.ok) {
        return { success: false, error: data.message || 'Erro ao confirmar exclusão' };
      }

      // Limpa dados locais após exclusão
      await this.logout();

      return { success: true };
    } catch (error) {
      console.error('Erro ao confirmar exclusão de conta:', error);
      return { success: false, error: 'Erro ao confirmar exclusão. Tente novamente.' };
    }
  }
}

export const authService = new AuthService();
