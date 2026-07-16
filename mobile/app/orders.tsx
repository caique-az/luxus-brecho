import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Image,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useAuthStore } from '../store/authStore';
import { useCartStore } from '../store/cartStore';
import { getApiUrl } from '../utils/networkUtils';
import { authService } from '../services/auth';
import { useToast } from '../contexts/ToastContext';
import ConfirmModal from '../components/ui/ConfirmModal';

interface CartItem {
  product_id: number;
  quantity: number;
  added_at: string;
  product: {
    id: number;
    titulo: string;
    preco: number;
    imagem_url: string;
    status: string;
    categoria: string;
  };
}

interface Cart {
  id?: string;
  user_id: number;
  items: CartItem[];
  created_at: string | null;
  updated_at: string | null;
}

export default function OrdersScreen() {
  const { user, isAuthenticated, initialize } = useAuthStore();
  const { clearCart: clearLocalCart } = useCartStore();
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [removingItem, setRemovingItem] = useState<number | null>(null);
  const [showClearModal, setShowClearModal] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [showCheckoutModal, setShowCheckoutModal] = useState(false);
  const { success: showSuccess, error: showError } = useToast();

  useEffect(() => {
    initialize();
  }, []);

  const fetchCart = async () => {
    if (!user) return;

    try {
      const response = await fetch(`${getApiUrl()}/cart/${user.id}`, {
        headers: await authService.getAuthHeaders(),
      });
      const data = await response.json();

      if (response.ok) {
        setCart(data);
      }
    } catch (error) {
      console.error('Erro ao buscar carrinho:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      if (isAuthenticated && user) {
        fetchCart();
      } else {
        setLoading(false);
      }
    }, [isAuthenticated, user])
  );

  const handleRefresh = () => {
    setRefreshing(true);
    fetchCart();
  };

  const handleRemoveItem = async (productId: number) => {
    if (!user) return;

    setRemovingItem(productId);

    try {
      const response = await fetch(`${getApiUrl()}/cart/${user.id}/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(await authService.getAuthHeaders()) },
        body: JSON.stringify({ product_id: productId }),
      });

      if (response.ok) {
        showSuccess('Item removido do carrinho');
        fetchCart();
      } else {
        showError('Erro ao remover item');
      }
    } catch (error) {
      showError('Erro ao remover item');
    } finally {
      setRemovingItem(null);
    }
  };

  const handleUpdateQuantity = async (productId: number, newQuantity: number) => {
    if (!user || newQuantity < 1) return;

    try {
      const response = await fetch(`${getApiUrl()}/cart/${user.id}/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...(await authService.getAuthHeaders()) },
        body: JSON.stringify({ product_id: productId, quantity: newQuantity }),
      });

      if (response.ok) {
        fetchCart();
      }
    } catch (error) {
      console.error('Erro ao atualizar quantidade:', error);
    }
  };

  const handleClearCart = async () => {
    if (!user) return;

    setClearing(true);
    setShowClearModal(false);

    try {
      const response = await fetch(`${getApiUrl()}/cart/${user.id}/clear`, {
        method: 'DELETE',
        headers: await authService.getAuthHeaders(),
      });

      if (response.ok) {
        showSuccess('Carrinho limpo com sucesso');
        clearLocalCart();
        fetchCart();
      } else {
        showError('Erro ao limpar carrinho');
      }
    } catch (error) {
      showError('Erro ao limpar carrinho');
    } finally {
      setClearing(false);
    }
  };

  const calculateTotal = () => {
    if (!cart?.items) return 0;
    return cart.items.reduce((total, item) => {
      return total + (item.product?.preco || 0) * item.quantity;
    }, 0);
  };

  if (!isAuthenticated) {
    return (
      <View style={{ flex: 1, backgroundColor: '#E91E63' }}>
        <SafeAreaView style={{ flex: 1, backgroundColor: '#f5f5f5' }}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color="white" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Meus Pedidos</Text>
            <View style={{ width: 40 }} />
          </View>

          <View style={styles.emptyContainer}>
            <Ionicons name="person-outline" size={64} color="#ccc" />
            <Text style={styles.emptyTitle}>Faça login para ver seus pedidos</Text>
            <Text style={styles.emptyText}>
              Entre na sua conta para acessar seu carrinho e histórico de pedidos.
            </Text>
            <TouchableOpacity
              style={styles.loginButton}
              onPress={() => router.push('/login')}
            >
              <Ionicons name="log-in-outline" size={20} color="white" />
              <Text style={styles.loginButtonText}>Fazer Login</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: '#E91E63' }}>
        <SafeAreaView style={{ flex: 1, backgroundColor: '#f5f5f5' }}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color="white" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Meus Pedidos</Text>
            <View style={{ width: 40 }} />
          </View>
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#E91E63" />
          </View>
        </SafeAreaView>
      </View>
    );
  }

  const hasItems = cart?.items && cart.items.length > 0;

  return (
    <View style={{ flex: 1, backgroundColor: '#E91E63' }}>
      <SafeAreaView style={{ flex: 1, backgroundColor: '#f5f5f5' }}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="white" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Meus Pedidos</Text>
          {hasItems && (
            <TouchableOpacity 
              onPress={() => setShowClearModal(true)}
              style={styles.clearButton}
            >
              <Ionicons name="trash-outline" size={20} color="white" />
            </TouchableOpacity>
          )}
          {!hasItems && <View style={{ width: 40 }} />}
        </View>

        {!hasItems ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="cart-outline" size={64} color="#ccc" />
            <Text style={styles.emptyTitle}>Seu carrinho está vazio</Text>
            <Text style={styles.emptyText}>
              Adicione produtos ao carrinho para vê-los aqui.
            </Text>
            <TouchableOpacity
              style={styles.shopButton}
              onPress={() => router.push('/(tabs)/products')}
            >
              <Ionicons name="shirt-outline" size={20} color="white" />
              <Text style={styles.shopButtonText}>Ver Produtos</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            <ScrollView
              style={styles.content}
              refreshControl={
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={handleRefresh}
                  colors={['#E91E63']}
                />
              }
            >
              {/* Lista de itens */}
              {cart?.items.map((item) => (
                <View key={item.product_id} style={styles.cartItem}>
                  <Image
                    source={{ uri: item.product?.imagem_url || 'https://via.placeholder.com/80' }}
                    style={styles.productImage}
                  />
                  <View style={styles.productInfo}>
                    <Text style={styles.productTitle} numberOfLines={2}>
                      {item.product?.titulo || 'Produto'}
                    </Text>
                    <Text style={styles.productCategory}>
                      {item.product?.categoria}
                    </Text>
                    <Text style={styles.productPrice}>
                      R$ {(item.product?.preco || 0).toFixed(2).replace('.', ',')}
                    </Text>
                    
                    {/* Controles de quantidade */}
                    <View style={styles.quantityContainer}>
                      <TouchableOpacity
                        style={styles.quantityButton}
                        onPress={() => handleUpdateQuantity(item.product_id, item.quantity - 1)}
                        disabled={item.quantity <= 1}
                      >
                        <Ionicons 
                          name="remove" 
                          size={16} 
                          color={item.quantity <= 1 ? '#ccc' : '#E91E63'} 
                        />
                      </TouchableOpacity>
                      <Text style={styles.quantityText}>{item.quantity}</Text>
                      <TouchableOpacity
                        style={styles.quantityButton}
                        onPress={() => handleUpdateQuantity(item.product_id, item.quantity + 1)}
                      >
                        <Ionicons name="add" size={16} color="#E91E63" />
                      </TouchableOpacity>
                    </View>
                  </View>
                  
                  <TouchableOpacity
                    style={styles.removeButton}
                    onPress={() => handleRemoveItem(item.product_id)}
                    disabled={removingItem === item.product_id}
                  >
                    {removingItem === item.product_id ? (
                      <ActivityIndicator size="small" color="#EF4444" />
                    ) : (
                      <Ionicons name="close-circle" size={24} color="#EF4444" />
                    )}
                  </TouchableOpacity>
                </View>
              ))}

              <View style={{ height: 120 }} />
            </ScrollView>

            {/* Footer com total */}
            <View style={styles.footer}>
              <View style={styles.totalContainer}>
                <Text style={styles.totalLabel}>Total:</Text>
                <Text style={styles.totalValue}>
                  R$ {calculateTotal().toFixed(2).replace('.', ',')}
                </Text>
              </View>
              <TouchableOpacity 
                style={styles.checkoutButton}
                onPress={() => setShowCheckoutModal(true)}
              >
                <Ionicons name="card-outline" size={20} color="white" />
                <Text style={styles.checkoutButtonText}>Finalizar Compra</Text>
              </TouchableOpacity>
            </View>
          </>
        )}

        {/* Modal de limpar carrinho */}
        <ConfirmModal
          visible={showClearModal}
          title="Limpar Carrinho"
          message="Tem certeza que deseja remover todos os itens do carrinho?"
          confirmText="Limpar"
          cancelText="Cancelar"
          icon="trash-outline"
          iconColor="#EF4444"
          isDestructive
          onConfirm={handleClearCart}
          onCancel={() => setShowClearModal(false)}
        />

        {/* Modal de Finalizar Compra */}
        <ConfirmModal
          visible={showCheckoutModal}
          title="Finalizar Compra"
          message={`Total: R$ ${calculateTotal().toFixed(2).replace('.', ',')}\n\nDeseja prosseguir com a compra?`}
          confirmText="CONFIRMAR"
          cancelText="CANCELAR"
          icon="cart"
          iconColor="#E91E63"
          onConfirm={() => {
            setShowCheckoutModal(false);
            const items = cart?.items.map(item => ({
              product_id: item.product_id,
              quantity: item.quantity,
            })) || [];
            router.push({
              pathname: '/checkout',
              params: {
                total: calculateTotal().toString(),
                items: JSON.stringify(items),
              },
            });
          }}
          onCancel={() => setShowCheckoutModal(false)}
        />
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    backgroundColor: '#E91E63',
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButton: {
    width: 40,
  },
  headerTitle: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  clearButton: {
    width: 40,
    alignItems: 'flex-end',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 16,
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
  },
  loginButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E91E63',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 8,
    gap: 8,
  },
  loginButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  shopButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E91E63',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 8,
    gap: 8,
  },
  shopButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  cartItem: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  productImage: {
    width: 80,
    height: 80,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
  },
  productInfo: {
    flex: 1,
    marginLeft: 12,
  },
  productTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  productCategory: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  productPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#E91E63',
    marginBottom: 8,
  },
  quantityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  quantityButton: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#f5f5f5',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  quantityText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    minWidth: 20,
    textAlign: 'center',
  },
  removeButton: {
    padding: 4,
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'white',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 5,
  },
  totalContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  totalLabel: {
    fontSize: 16,
    color: '#666',
  },
  totalValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#E91E63',
  },
  checkoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E91E63',
    paddingVertical: 16,
    borderRadius: 12,
    gap: 8,
  },
  checkoutButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
