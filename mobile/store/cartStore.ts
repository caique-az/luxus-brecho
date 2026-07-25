import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { CONFIG } from '../constants/config';
import { Product } from '../types/product';
import { getApiUrl } from '../utils/networkUtils';
import { logger } from '../utils/logger';
import { authService } from '../services/auth';

export interface CartItem {
  id: number;
  titulo: string;
  preco: number;
  imagem?: string;
  quantity: number;
  categoria?: string;
}

export interface CartState {
  cart: CartItem[];
  loading: boolean;
  getTotalItems: () => number;
  getSubtotal: () => number;
  getShippingCost: () => number;
  getTotal: () => number;
  addToCart: (product: Product, userId?: number) => Promise<void>;
  removeFromCart: (productId: number, userId?: number) => Promise<void>;
  updateQuantity: (productId: number, quantity: number) => Promise<void>;
  loadCart: () => Promise<void>;
  clearCart: () => Promise<void>;
  getItemQuantity: (productId: number) => number;
  isInCart: (productId: number) => boolean;
  syncWithServer: (userId: number) => Promise<void>;
  loadFromServer: (userId: number) => Promise<void>;
}

export const useCartStore = create<CartState>((set, get) => ({
  // Estado
  cart: [],
  loading: false,
  
  // Getters computados
  getTotalItems: () => {
    return get().cart.reduce((total, item) => total + item.quantity, 0);
  },
  
  getSubtotal: () => {
    return get().cart.reduce((total, item) => total + (item.preco * item.quantity), 0);
  },
  
  getShippingCost: () => {
    const subtotal = get().getSubtotal();
    return subtotal >= CONFIG.CART.FREE_SHIPPING_THRESHOLD ? 0 : CONFIG.CART.SHIPPING_FEE;
  },
  
  getTotal: () => {
    return get().getSubtotal() + get().getShippingCost();
  },
  
  // Ações
  addToCart: async (product: Product, userId?: number) => {
    set({ loading: true });
    try {
      const currentCart = get().cart;
      const existingItemIndex = currentCart.findIndex(item => item.id === product.id);
      
      let updatedCart;
      if (existingItemIndex >= 0) {
        // Produto já existe no carrinho - não faz nada (peças únicas)
        logger.info('Produto já está no carrinho. Cada peça é única.', 'CART');
        set({ loading: false });
        return;
      } else {
        // Se é um produto novo, adiciona com quantidade 1 (sempre 1, peças únicas)
        const cartItem = {
          id: product.id,
          titulo: product.titulo,
          preco: Number(product.preco) || 0,
          imagem: product.imagem,
          quantity: 1
        };
        updatedCart = [...currentCart, cartItem];
      }
      
      set({ cart: updatedCart });
      await AsyncStorage.setItem(CONFIG.CART.STORAGE_KEY, JSON.stringify(updatedCart));
      
      // Sincroniza com o servidor se usuário estiver logado
      if (userId) {
        try {
          await fetch(`${getApiUrl()}/cart/${userId}/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...(await authService.getAuthHeaders()) },
            body: JSON.stringify({ product_id: product.id, quantity: 1 }),
          });
        } catch (e) {
          logger.warn('Erro ao sincronizar com servidor', 'CART', { error: e });
        }
      }
    } catch (error) {
      logger.error('Erro ao adicionar produto ao carrinho', error as Error, 'CART');
    } finally {
      set({ loading: false });
    }
  },
  
  removeFromCart: async (productId: number, userId?: number) => {
    set({ loading: true });
    try {
      const updatedCart = get().cart.filter(item => item.id !== productId);
      set({ cart: updatedCart });
      await AsyncStorage.setItem(CONFIG.CART.STORAGE_KEY, JSON.stringify(updatedCart));
      
      // Sincroniza com o servidor se usuário estiver logado
      if (userId) {
        try {
          await fetch(`${getApiUrl()}/cart/${userId}/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...(await authService.getAuthHeaders()) },
            body: JSON.stringify({ product_id: productId }),
          });
        } catch (e) {
          logger.warn('Erro ao sincronizar com servidor', 'CART', { error: e });
        }
      }
    } catch (error) {
      logger.error('Erro ao remover produto do carrinho', error as Error, 'CART');
    } finally {
      set({ loading: false });
    }
  },
  
  updateQuantity: async (productId: number, quantity: number) => {
    if (quantity <= 0) {
      await get().removeFromCart(productId);
      return;
    }
    
    set({ loading: true });
    try {
      const updatedCart = get().cart.map(item => 
        item.id === productId 
          ? { ...item, quantity: quantity }
          : item
      );
      set({ cart: updatedCart });
      await AsyncStorage.setItem(CONFIG.CART.STORAGE_KEY, JSON.stringify(updatedCart));
    } catch (error) {
      logger.error('Erro ao atualizar quantidade', error as Error, 'CART');
    } finally {
      set({ loading: false });
    }
  },
  
  loadCart: async () => {
    set({ loading: true });
    try {
      const savedCart = await AsyncStorage.getItem(CONFIG.CART.STORAGE_KEY);
      if (savedCart) {
        const parsedCart = JSON.parse(savedCart);
        set({ cart: parsedCart });
      }
    } catch (error) {
      logger.error('Erro ao carregar carrinho', error as Error, 'CART');
    } finally {
      set({ loading: false });
    }
  },
  
  clearCart: async () => {
    set({ loading: true });
    try {
      set({ cart: [] });
      await AsyncStorage.removeItem(CONFIG.CART.STORAGE_KEY);
    } catch (error) {
      logger.error('Erro ao limpar carrinho', error as Error, 'CART');
    } finally {
      set({ loading: false });
    }
  },

  getItemQuantity: (productId: number) => {
    const item = get().cart.find(item => item.id === productId);
    return item ? item.quantity : 0;
  },

  isInCart: (productId: number) => {
    return get().cart.some(item => item.id === productId);
  },

  syncWithServer: async (userId: number) => {
    try {
      const currentCart = get().cart;
      const items = currentCart.map(item => ({
        product_id: item.id,
        quantity: item.quantity,
      }));
      
      await fetch(`${getApiUrl()}/cart/${userId}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(await authService.getAuthHeaders()) },
        body: JSON.stringify({ items }),
      });
    } catch (error) {
      logger.error('Erro ao sincronizar carrinho', error as Error, 'CART');
    }
  },

  loadFromServer: async (userId: number) => {
    set({ loading: true });
    try {
      const response = await fetch(`${getApiUrl()}/cart/${userId}`, {
        headers: await authService.getAuthHeaders(),
      });
      const data = await response.json();
      
      if (response.ok && data.items) {
        const cartItems: CartItem[] = data.items.map((item: any) => ({
          id: item.product_id,
          titulo: item.product?.titulo || 'Produto',
          preco: item.product?.preco || 0,
          imagem: item.product?.imagem,  // Corrigido: era imagem_url
          quantity: item.quantity,
          categoria: item.product?.categoria,
        }));
        
        set({ cart: cartItems });
        await AsyncStorage.setItem(CONFIG.CART.STORAGE_KEY, JSON.stringify(cartItems));
      }
    } catch (error) {
      logger.error('Erro ao carregar carrinho do servidor', error as Error, 'CART');
    } finally {
      set({ loading: false });
    }
  },
}));
