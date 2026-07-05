import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useAuthStore } from '../store/authStore';
import { useCartStore } from '../store/cartStore';
import { getApiUrl } from '../utils/networkUtils';
import { authService } from '../services/auth';
import ConfirmModal from '../components/ui/ConfirmModal';

interface Address {
  rua: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  estado: string;
  cep: string;
}

export default function CheckoutScreen() {
  const { user, isAuthenticated } = useAuthStore();
  const { clearCart } = useCartStore();
  const params = useLocalSearchParams();
  const total = params.total ? parseFloat(params.total as string) : 0;
  const itemsParam = params.items ? JSON.parse(params.items as string) : [];

  const [address, setAddress] = useState<Address>({
    rua: '',
    numero: '',
    complemento: '',
    bairro: '',
    cidade: '',
    estado: '',
    cep: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [loadingAddress, setLoadingAddress] = useState(true);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    loadUserAddress();
  }, [isAuthenticated]);

  const loadUserAddress = async () => {
    if (!user) return;
    
    try {
      // Tenta carregar endereço salvo do usuário
      const response = await fetch(`${getApiUrl()}/users/${user.id}`, {
        headers: await authService.getAuthHeaders(),
      });
      const data = await response.json();
      
      if (response.ok && data.endereco) {
        setAddress({
          rua: data.endereco.rua || '',
          numero: data.endereco.numero || '',
          complemento: data.endereco.complemento || '',
          bairro: data.endereco.bairro || '',
          cidade: data.endereco.cidade || '',
          estado: data.endereco.estado || '',
          cep: data.endereco.cep || '',
        });
      }
    } catch (error) {
      console.log('Erro ao carregar endereço:', error);
    } finally {
      setLoadingAddress(false);
    }
  };

  const validateAddress = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!address.rua.trim()) newErrors.rua = 'Rua é obrigatória';
    if (!address.numero.trim()) newErrors.numero = 'Número é obrigatório';
    if (!address.bairro.trim()) newErrors.bairro = 'Bairro é obrigatório';
    if (!address.cidade.trim()) newErrors.cidade = 'Cidade é obrigatória';
    if (!address.estado.trim()) newErrors.estado = 'Estado é obrigatório';
    if (!address.cep.trim()) newErrors.cep = 'CEP é obrigatório';
    else if (!/^\d{5}-?\d{3}$/.test(address.cep.replace(/\D/g, '').replace(/(\d{5})(\d{3})/, '$1-$2'))) {
      newErrors.cep = 'CEP inválido';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleConfirmAddress = () => {
    if (!validateAddress()) return;
    setShowConfirmModal(true);
  };

  const handleCreateOrder = async () => {
    if (!user) return;
    
    setShowConfirmModal(false);
    setLoading(true);

    try {
      const response = await fetch(`${getApiUrl()}/orders/user/${user.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(await authService.getAuthHeaders()) },
        body: JSON.stringify({
          items: itemsParam,
          endereco: address,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Limpa o carrinho local
        await clearCart();
        setShowSuccessModal(true);
      } else {
        alert(data.message || 'Erro ao criar pedido');
      }
    } catch (error) {
      console.error('Erro ao criar pedido:', error);
      alert('Erro de conexão. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  const handleSuccessClose = () => {
    setShowSuccessModal(false);
    router.replace('/orders');
  };

  const handleInputChange = (field: keyof Address, value: string) => {
    setAddress(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const formatCEP = (value: string) => {
    const numbers = value.replace(/\D/g, '');
    if (numbers.length <= 5) return numbers;
    return `${numbers.slice(0, 5)}-${numbers.slice(5, 8)}`;
  };

  if (loadingAddress) {
    return (
      <View style={{ flex: 1, backgroundColor: '#E91E63' }}>
        <SafeAreaView style={{ flex: 1, backgroundColor: '#f5f5f5' }}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color="white" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Finalizar Compra</Text>
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
          <Text style={styles.headerTitle}>Finalizar Compra</Text>
          <View style={{ width: 40 }} />
        </View>

        <KeyboardAvoidingView
          style={{ flex: 1 }}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
            {/* Resumo do Pedido */}
            <View style={styles.summaryCard}>
              <View style={styles.summaryHeader}>
                <Ionicons name="cart" size={24} color="#E91E63" />
                <Text style={styles.summaryTitle}>Resumo do Pedido</Text>
              </View>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Itens:</Text>
                <Text style={styles.summaryValue}>{itemsParam.length}</Text>
              </View>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Total:</Text>
                <Text style={styles.summaryTotal}>
                  R$ {total.toFixed(2).replace('.', ',')}
                </Text>
              </View>
            </View>

            {/* Endereço de Entrega */}
            <View style={styles.addressCard}>
              <View style={styles.addressHeader}>
                <Ionicons name="location" size={24} color="#E91E63" />
                <Text style={styles.addressTitle}>Endereço de Entrega</Text>
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.label}>CEP *</Text>
                <TextInput
                  style={[styles.input, errors.cep && styles.inputError]}
                  value={address.cep}
                  onChangeText={(value) => handleInputChange('cep', formatCEP(value))}
                  placeholder="00000-000"
                  keyboardType="numeric"
                  maxLength={9}
                />
                {errors.cep && <Text style={styles.errorText}>{errors.cep}</Text>}
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.label}>Rua *</Text>
                <TextInput
                  style={[styles.input, errors.rua && styles.inputError]}
                  value={address.rua}
                  onChangeText={(value) => handleInputChange('rua', value)}
                  placeholder="Nome da rua"
                />
                {errors.rua && <Text style={styles.errorText}>{errors.rua}</Text>}
              </View>

              <View style={styles.row}>
                <View style={[styles.formGroup, { flex: 1, marginRight: 8 }]}>
                  <Text style={styles.label}>Número *</Text>
                  <TextInput
                    style={[styles.input, errors.numero && styles.inputError]}
                    value={address.numero}
                    onChangeText={(value) => handleInputChange('numero', value)}
                    placeholder="Nº"
                    keyboardType="numeric"
                  />
                  {errors.numero && <Text style={styles.errorText}>{errors.numero}</Text>}
                </View>

                <View style={[styles.formGroup, { flex: 2 }]}>
                  <Text style={styles.label}>Complemento</Text>
                  <TextInput
                    style={styles.input}
                    value={address.complemento}
                    onChangeText={(value) => handleInputChange('complemento', value)}
                    placeholder="Apto, bloco, etc."
                  />
                </View>
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.label}>Bairro *</Text>
                <TextInput
                  style={[styles.input, errors.bairro && styles.inputError]}
                  value={address.bairro}
                  onChangeText={(value) => handleInputChange('bairro', value)}
                  placeholder="Nome do bairro"
                />
                {errors.bairro && <Text style={styles.errorText}>{errors.bairro}</Text>}
              </View>

              <View style={styles.row}>
                <View style={[styles.formGroup, { flex: 2, marginRight: 8 }]}>
                  <Text style={styles.label}>Cidade *</Text>
                  <TextInput
                    style={[styles.input, errors.cidade && styles.inputError]}
                    value={address.cidade}
                    onChangeText={(value) => handleInputChange('cidade', value)}
                    placeholder="Nome da cidade"
                  />
                  {errors.cidade && <Text style={styles.errorText}>{errors.cidade}</Text>}
                </View>

                <View style={[styles.formGroup, { flex: 1 }]}>
                  <Text style={styles.label}>Estado *</Text>
                  <TextInput
                    style={[styles.input, errors.estado && styles.inputError]}
                    value={address.estado}
                    onChangeText={(value) => handleInputChange('estado', value.toUpperCase())}
                    placeholder="UF"
                    maxLength={2}
                    autoCapitalize="characters"
                  />
                  {errors.estado && <Text style={styles.errorText}>{errors.estado}</Text>}
                </View>
              </View>
            </View>

            <View style={{ height: 100 }} />
          </ScrollView>
        </KeyboardAvoidingView>

        {/* Footer */}
        <View style={styles.footer}>
          <TouchableOpacity
            style={[styles.confirmButton, loading && styles.buttonDisabled]}
            onPress={handleConfirmAddress}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <>
                <Ionicons name="checkmark-circle" size={20} color="white" />
                <Text style={styles.confirmButtonText}>Confirmar Pedido</Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        {/* Modal de Confirmação */}
        <ConfirmModal
          visible={showConfirmModal}
          title="Finalizar Compra"
          message={`Total: R$ ${total.toFixed(2).replace('.', ',')}\n\nDeseja prosseguir com a compra?`}
          confirmText="CONFIRMAR"
          cancelText="CANCELAR"
          icon="cart"
          iconColor="#E91E63"
          onConfirm={handleCreateOrder}
          onCancel={() => setShowConfirmModal(false)}
        />

        {/* Modal de Sucesso */}
        <ConfirmModal
          visible={showSuccessModal}
          title="Sucesso!"
          message="Pedido realizado com sucesso!"
          confirmText="OK"
          cancelText=""
          icon="checkmark-circle"
          iconColor="#22C55E"
          onConfirm={handleSuccessClose}
          onCancel={handleSuccessClose}
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
  content: {
    flex: 1,
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  summaryCard: {
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
  summaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 8,
  },
  summaryTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  summaryLabel: {
    fontSize: 14,
    color: '#666',
  },
  summaryValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  summaryTotal: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#E91E63',
  },
  addressCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  addressHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 8,
  },
  addressTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  formGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#f8f9fa',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
    color: '#333',
  },
  inputError: {
    borderColor: '#EF4444',
  },
  errorText: {
    color: '#EF4444',
    fontSize: 12,
    marginTop: 4,
  },
  row: {
    flexDirection: 'row',
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
  confirmButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E91E63',
    paddingVertical: 16,
    borderRadius: 12,
    gap: 8,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  confirmButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
