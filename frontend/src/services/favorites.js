import api from './api';

/**
 * Service para gerenciar favoritos via API.
 *
 * A identidade do usuário vai no Bearer token, injetado pelo interceptor de
 * `api.js` — como nos demais services. O header `X-User-Id` que este arquivo
 * montava à mão era do esquema antigo, removido do backend por ser falsificável
 * (as rotas de favoritos são `@jwt_required` e leem `g.user_id`).
 */

export const favoritesService = {
  /**
   * Busca todos os favoritos do usuário
   * @returns {Promise<Array>} Lista de favoritos com detalhes dos produtos
   */
  async getFavorites() {
    try {
      const response = await api.get('/favorites');
      return {
        success: true,
        favorites: response.data.favorites || [],
        total: response.data.total || 0
      };
    } catch (error) {
      console.error('Erro ao buscar favoritos:', error);
      return {
        success: false,
        error: error.response?.data?.message || 'Erro ao buscar favoritos',
        favorites: [],
        total: 0
      };
    }
  },

  /**
   * Adiciona um produto aos favoritos
   * @param {number} productId - ID do produto
   * @returns {Promise<Object>} Resultado da operação
   */
  async addFavorite(productId) {
    try {
      const response = await api.post('/favorites', { product_id: productId });
      return {
        success: true,
        message: response.data.message,
        favorite: response.data.favorite
      };
    } catch (error) {
      console.error('Erro ao adicionar favorito:', error);
      const isAlreadyFavorite = error.response?.status === 409;
      return {
        success: false,
        alreadyFavorite: isAlreadyFavorite,
        error: error.response?.data?.message || 'Erro ao adicionar favorito'
      };
    }
  },

  /**
   * Remove um produto dos favoritos
   * @param {number} productId - ID do produto
   * @returns {Promise<Object>} Resultado da operação
   */
  async removeFavorite(productId) {
    try {
      const response = await api.delete(`/favorites/${productId}`);
      return {
        success: true,
        message: response.data.message
      };
    } catch (error) {
      console.error('Erro ao remover favorito:', error);
      return {
        success: false,
        error: error.response?.data?.message || 'Erro ao remover favorito'
      };
    }
  },

  /**
   * Verifica se um produto está nos favoritos
   * @param {number} productId - ID do produto
   * @returns {Promise<boolean>} True se está favoritado
   */
  async isFavorited(productId) {
    try {
      const response = await api.get(`/favorites/check/${productId}`);
      return response.data.is_favorited || false;
    } catch (error) {
      console.error('Erro ao verificar favorito:', error);
      return false;
    }
  },

  /**
   * Alterna o estado de favorito (adiciona ou remove)
   * @param {number} productId - ID do produto
   * @returns {Promise<Object>} Resultado da operação
   */
  async toggleFavorite(productId) {
    try {
      const response = await api.post('/favorites/toggle', { product_id: productId });
      return {
        success: true,
        message: response.data.message,
        isFavorited: response.data.is_favorited,
        favorite: response.data.favorite
      };
    } catch (error) {
      console.error('Erro ao alternar favorito:', error);
      return {
        success: false,
        error: error.response?.data?.message || 'Erro ao alternar favorito'
      };
    }
  }
};

export default favoritesService;
