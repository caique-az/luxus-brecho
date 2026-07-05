import React, { useState, useCallback } from 'react';
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
import { getApiUrl } from '../utils/networkUtils';
import { authService } from '../services/auth';

interface OrderItem {
  product_id: number;
  quantity: number;
  preco_unitario: number;
  preco_total: number;
  titulo: string;
  imagem_url: string;
}

interface Order {
  id: number;
  user_id: number;
  items: OrderItem[];
  total: number;
  status: string;
  endereco: {
    rua: string;
    numero: string;
    complemento?: string;
    bairro: string;
    cidade: string;
    estado: string;
    cep: string;
  };
  created_at: string;
  updated_at: string;
}

const STATUS_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  pendente: { label: 'Pendente', color: '#F59E0B', icon: 'time-outline' },
  confirmado: { label: 'Confirmado', color: '#3B82F6', icon: 'checkmark-circle-outline' },
  em_preparacao: { label: 'Em Preparação', color: '#8B5CF6', icon: 'cube-outline' },
  enviado: { label: 'Enviado', color: '#06B6D4', icon: 'airplane-outline' },
  entregue: { label: 'Entregue', color: '#22C55E', icon: 'checkmark-done-circle-outline' },
  cancelado: { label: 'Cancelado', color: '#EF4444', icon: 'close-circle-outline' },
};

export default function OrderHistoryScreen() {
  const { user, isAuthenticated, initialize } = useAuthStore();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchOrders = async () => {
    if (!user) return;

    try {
      const response = await fetch(`${getApiUrl()}/orders/user/${user.id}`, {
        headers: await authService.getAuthHeaders(),
      });
      const data = await response.json();

      if (response.ok) {
        setOrders(data.orders || []);
      }
    } catch (error) {
      console.error('Erro ao buscar pedidos:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      initialize();
      if (isAuthenticated && user) {
        fetchOrders();
      } else {
        setLoading(false);
      }
    }, [isAuthenticated, user])
  );

  const handleRefresh = () => {
    setRefreshing(true);
    fetchOrders();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
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
              Entre na sua conta para acessar seu histórico de pedidos.
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

  return (
    <View style={{ flex: 1, backgroundColor: '#E91E63' }}>
      <SafeAreaView style={{ flex: 1, backgroundColor: '#f5f5f5' }}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="white" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Meus Pedidos</Text>
          <View style={{ width: 40 }} />
        </View>

        {orders.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="receipt-outline" size={64} color="#ccc" />
            <Text style={styles.emptyTitle}>Nenhum pedido realizado</Text>
            <Text style={styles.emptyText}>
              Você ainda não fez nenhum pedido. Explore nossos produtos!
            </Text>
            <TouchableOpacity
              style={styles.shopButton}
              onPress={() => router.push('/(tabs)/products')}
            >
              <Ionicons name="storefront-outline" size={20} color="white" />
              <Text style={styles.shopButtonText}>Ver Produtos</Text>
            </TouchableOpacity>
          </View>
        ) : (
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
            {orders.map((order) => {
              const defaultStatus = { label: 'Pendente', color: '#F59E0B', icon: 'time-outline' };
              const statusInfo = STATUS_LABELS[order.status] || defaultStatus;
              
              return (
                <View key={order.id} style={styles.orderCard}>
                  {/* Header do Pedido */}
                  <View style={styles.orderHeader}>
                    <View>
                      <Text style={styles.orderNumber}>Pedido #{order.id}</Text>
                      <Text style={styles.orderDate}>{formatDate(order.created_at)}</Text>
                    </View>
                    <View style={[styles.statusBadge, { backgroundColor: statusInfo.color + '20' }]}>
                      <Ionicons name={statusInfo.icon as any} size={14} color={statusInfo.color} />
                      <Text style={[styles.statusText, { color: statusInfo.color }]}>
                        {statusInfo.label}
                      </Text>
                    </View>
                  </View>

                  {/* Itens do Pedido */}
                  <View style={styles.orderItems}>
                    {order.items.slice(0, 2).map((item, index) => (
                      <View key={index} style={styles.orderItem}>
                        <Image
                          source={{ uri: item.imagem_url || 'https://via.placeholder.com/50' }}
                          style={styles.itemImage}
                        />
                        <View style={styles.itemInfo}>
                          <Text style={styles.itemTitle} numberOfLines={1}>
                            {item.titulo}
                          </Text>
                          <Text style={styles.itemPrice}>
                            R$ {item.preco_unitario.toFixed(2).replace('.', ',')}
                          </Text>
                        </View>
                      </View>
                    ))}
                    {order.items.length > 2 && (
                      <Text style={styles.moreItems}>
                        +{order.items.length - 2} item(s)
                      </Text>
                    )}
                  </View>

                  {/* Endereço */}
                  <View style={styles.addressContainer}>
                    <Ionicons name="location-outline" size={16} color="#666" />
                    <Text style={styles.addressText} numberOfLines={1}>
                      {order.endereco.rua}, {order.endereco.numero} - {order.endereco.bairro}
                    </Text>
                  </View>

                  {/* Footer do Pedido */}
                  <View style={styles.orderFooter}>
                    <Text style={styles.totalLabel}>Total:</Text>
                    <Text style={styles.totalValue}>
                      R$ {order.total.toFixed(2).replace('.', ',')}
                    </Text>
                  </View>
                </View>
              );
            })}

            <View style={{ height: 20 }} />
          </ScrollView>
        )}
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
  orderCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  orderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  orderNumber: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  orderDate: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  orderItems: {
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    paddingTop: 12,
    marginBottom: 12,
  },
  orderItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  itemImage: {
    width: 50,
    height: 50,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
  },
  itemInfo: {
    flex: 1,
    marginLeft: 12,
  },
  itemTitle: {
    fontSize: 14,
    color: '#333',
    marginBottom: 2,
  },
  itemPrice: {
    fontSize: 14,
    fontWeight: '600',
    color: '#E91E63',
  },
  moreItems: {
    fontSize: 12,
    color: '#666',
    fontStyle: 'italic',
    marginTop: 4,
  },
  addressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
    gap: 8,
  },
  addressText: {
    flex: 1,
    fontSize: 12,
    color: '#666',
  },
  orderFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    paddingTop: 12,
  },
  totalLabel: {
    fontSize: 14,
    color: '#666',
  },
  totalValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#E91E63',
  },
});
