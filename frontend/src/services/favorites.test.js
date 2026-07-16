import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('./api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import api from './api';
import { favoritesService } from './favorites';

/**
 * Regressão de FE-01: o service montava um header `X-User-Id` à mão. O backend
 * removeu esse esquema (favoritos são `@jwt_required` e leem `g.user_id`), e o
 * Bearer já vai pelo interceptor de api.js — o header era ruído que sugeria uma
 * autenticação que não existe mais.
 */
describe('favoritesService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('não envia mais o header X-User-Id', () => {
    it('getFavorites chama a API sem headers próprios', async () => {
      api.get.mockResolvedValue({ data: { favorites: [], total: 0 } });

      await favoritesService.getFavorites();

      expect(api.get).toHaveBeenCalledWith('/favorites');
    });

    it('addFavorite manda só o corpo', async () => {
      api.post.mockResolvedValue({ data: { message: 'ok', favorite: { id: 1 } } });

      await favoritesService.addFavorite(7);

      expect(api.post).toHaveBeenCalledWith('/favorites', { product_id: 7 });
    });

    it('removeFavorite chama a URL sem headers', async () => {
      api.delete.mockResolvedValue({ data: { message: 'removido' } });

      await favoritesService.removeFavorite(7);

      expect(api.delete).toHaveBeenCalledWith('/favorites/7');
    });

    it('toggleFavorite manda só o corpo', async () => {
      api.post.mockResolvedValue({ data: { message: 'ok', is_favorited: true } });

      await favoritesService.toggleFavorite(7);

      expect(api.post).toHaveBeenCalledWith('/favorites/toggle', { product_id: 7 });
    });

    it('nenhuma chamada carrega X-User-Id', async () => {
      api.get.mockResolvedValue({ data: { favorites: [], total: 0, is_favorited: false } });
      api.post.mockResolvedValue({ data: {} });
      api.delete.mockResolvedValue({ data: {} });

      await favoritesService.getFavorites();
      await favoritesService.addFavorite(1);
      await favoritesService.removeFavorite(1);
      await favoritesService.isFavorited(1);
      await favoritesService.toggleFavorite(1);

      const todasAsChamadas = [
        ...api.get.mock.calls,
        ...api.post.mock.calls,
        ...api.delete.mock.calls,
      ];
      const serializado = JSON.stringify(todasAsChamadas);
      expect(serializado).not.toContain('X-User-Id');
      expect(serializado).not.toContain('headers');
    });
  });

  describe('sem usuário logado, quem decide é o backend', () => {
    it('não lança erro local — a chamada sai e o 401 é tratado', async () => {
      // Antes, um guard local lançava 'Usuário não autenticado' antes de qualquer
      // rede. Nenhum outro service do projeto faz isso: o Bearer (ou a falta dele)
      // é assunto do interceptor.
      localStorage.getItem.mockReturnValue(null);
      api.get.mockRejectedValue({ response: { status: 401, data: { message: 'Token inválido' } } });

      const r = await favoritesService.getFavorites();

      expect(api.get).toHaveBeenCalledWith('/favorites');
      expect(r.success).toBe(false);
      expect(r.favorites).toEqual([]);
    });
  });

  describe('erros da API viram retorno tratado', () => {
    it('409 marca alreadyFavorite', async () => {
      api.post.mockRejectedValue({ response: { status: 409, data: { message: 'Já favoritado' } } });

      const r = await favoritesService.addFavorite(7);

      expect(r.success).toBe(false);
      expect(r.alreadyFavorite).toBe(true);
    });

    it('isFavorited devolve false quando a chamada falha', async () => {
      api.get.mockRejectedValue({ response: { status: 500 } });

      await expect(favoritesService.isFavorited(7)).resolves.toBe(false);
    });
  });
});
