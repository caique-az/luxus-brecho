import AsyncStorage from '@react-native-async-storage/async-storage';
import { getApiUrl } from '../utils/networkUtils';
import { CONFIG } from '../constants/config';
import { authService } from './auth';

const API_BASE_URL = getApiUrl();

/**
 * Service para gerenciar favoritos via API.
 * Todas as requisições incluem o X-User-Id do usuário logado.
 */

// Função auxiliar para obter user_id
const getUserId = async (): Promise<string | null> => {
  try {
    const userStr = await AsyncStorage.getItem('@luxus_brecho:user_data');
    if (userStr) {
      const user = JSON.parse(userStr);
      return user.id || user._id;
    }
  } catch (error) {
    console.error('Erro ao obter user_id:', error);
  }
  return null;
};

// Função auxiliar para fazer requisições com X-User-Id
const fetchWithUserId = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> => {
  const userId = await getUserId();
  
  if (!userId) {
    throw new Error('Usuário não autenticado');
  }

  const authHeaders = await authService.getAuthHeaders();
  const headers = {
    'Content-Type': 'application/json',
    'X-User-Id': userId,
    ...authHeaders,
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  return response;
};

export interface FavoriteProduct {
  id: number;
  titulo: string;
  preco: number;
  imagem: string;
  categoria: string;
  descricao?: string;
}

export interface FavoriteItem {
  _id: string;
  user_id: string;
  product_id: number;
  created_at: string;
  product: FavoriteProduct | null;
}

export interface FavoritesResponse {
  favorites: FavoriteItem[];
  total: number;
}

export const favoritesService = {
  /**
   * Busca todos os favoritos do usuário
   */
  async getFavorites(): Promise<{ success: boolean; favorites: FavoriteItem[]; total: number; error?: string }> {
    try {
      const response = await fetchWithUserId('/favorites');

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          success: false,
          favorites: [],
          total: 0,
          error: errorData.message || 'Erro ao buscar favoritos',
        };
      }

      const data: FavoritesResponse = await response.json();
      
      if (CONFIG.DEBUG.ENABLE_API_LOGS) {
        console.log('✅ Favoritos carregados:', data.total);
      }

      return {
        success: true,
        favorites: data.favorites || [],
        total: data.total || 0,
      };
    } catch (error) {
      console.error('Erro ao buscar favoritos:', error);
      return {
        success: false,
        favorites: [],
        total: 0,
        error: error instanceof Error ? error.message : 'Erro ao buscar favoritos',
      };
    }
  },

  /**
   * Adiciona um produto aos favoritos
   */
  async addFavorite(productId: number): Promise<{ success: boolean; alreadyFavorite?: boolean; error?: string }> {
    try {
      const response = await fetchWithUserId('/favorites', {
        method: 'POST',
        body: JSON.stringify({ product_id: productId }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const isAlreadyFavorite = response.status === 409;
        
        return {
          success: false,
          alreadyFavorite: isAlreadyFavorite,
          error: errorData.message || 'Erro ao adicionar favorito',
        };
      }

      if (CONFIG.DEBUG.ENABLE_API_LOGS) {
        console.log('✅ Produto adicionado aos favoritos:', productId);
      }

      return { success: true };
    } catch (error) {
      console.error('Erro ao adicionar favorito:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Erro ao adicionar favorito',
      };
    }
  },

  /**
   * Remove um produto dos favoritos
   */
  async removeFavorite(productId: number): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await fetchWithUserId(`/favorites/${productId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          success: false,
          error: errorData.message || 'Erro ao remover favorito',
        };
      }

      if (CONFIG.DEBUG.ENABLE_API_LOGS) {
        console.log('✅ Produto removido dos favoritos:', productId);
      }

      return { success: true };
    } catch (error) {
      console.error('Erro ao remover favorito:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Erro ao remover favorito',
      };
    }
  },

  /**
   * Verifica se um produto está nos favoritos
   */
  async isFavorited(productId: number): Promise<boolean> {
    try {
      const response = await fetchWithUserId(`/favorites/check/${productId}`);

      if (!response.ok) {
        return false;
      }

      const data = await response.json();
      return data.is_favorited || false;
    } catch (error) {
      console.error('Erro ao verificar favorito:', error);
      return false;
    }
  },

  /**
   * Alterna o estado de favorito (adiciona ou remove)
   */
  async toggleFavorite(productId: number): Promise<{ success: boolean; isFavorited?: boolean; error?: string }> {
    try {
      const response = await fetchWithUserId('/favorites/toggle', {
        method: 'POST',
        body: JSON.stringify({ product_id: productId }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          success: false,
          error: errorData.message || 'Erro ao alternar favorito',
        };
      }

      const data = await response.json();
      
      if (CONFIG.DEBUG.ENABLE_API_LOGS) {
        console.log('✅ Favorito alternado:', productId, data.is_favorited);
      }

      return {
        success: true,
        isFavorited: data.is_favorited,
      };
    } catch (error) {
      console.error('Erro ao alternar favorito:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Erro ao alternar favorito',
      };
    }
  },
};
