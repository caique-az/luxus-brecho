import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useCartStore } from '../../store/cartStore';
import { useToastContext } from '../../contexts/ToastContext';
import { buscarCep } from '../../services/cep';
import api from '../../services/api';
import ConfirmModal from '../../components/ConfirmModal';
import { 
  FiArrowLeft, 
  FiShoppingCart, 
  FiMapPin, 
  FiCheck,
  FiPackage
} from 'react-icons/fi';
import './index.css';

const Checkout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated } = useAuthStore();
  const { clearCart, getSubtotal, getShippingCost, getTotal, cart } = useCartStore();
  const { success: showSuccess, error: showError } = useToastContext();

  // Dados do carrinho passados via state ou calculados
  const cartItems = location.state?.items || cart;
  const total = location.state?.total || getTotal();

  const [address, setAddress] = useState({
    rua: '',
    numero: '',
    complemento: '',
    bairro: '',
    cidade: '',
    estado: '',
    cep: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [loadingAddress, setLoadingAddress] = useState(true);
  const [loadingCep, setLoadingCep] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    loadUserAddress();
  }, [isAuthenticated, navigate]);

  const loadUserAddress = async () => {
    if (!user) return;
    
    try {
      const { data } = await api.get(`/users/${user.id}`);

      if (data.endereco) {
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

  const handleCepBlur = async () => {
    const cepLimpo = address.cep.replace(/\D/g, '');
    if (cepLimpo.length !== 8) return;

    setLoadingCep(true);
    try {
      const dados = await buscarCep(cepLimpo);
      if (dados) {
        setAddress(prev => ({
          ...prev,
          rua: dados.logradouro || prev.rua,
          bairro: dados.bairro || prev.bairro,
          cidade: dados.localidade || prev.cidade,
          estado: dados.uf || prev.estado,
        }));
      }
    } catch (error) {
      console.log('Erro ao buscar CEP:', error);
    } finally {
      setLoadingCep(false);
    }
  };

  const validateAddress = () => {
    const newErrors = {};
    
    if (!address.rua.trim()) newErrors.rua = 'Rua é obrigatória';
    if (!address.numero.trim()) newErrors.numero = 'Número é obrigatório';
    if (!address.bairro.trim()) newErrors.bairro = 'Bairro é obrigatório';
    if (!address.cidade.trim()) newErrors.cidade = 'Cidade é obrigatória';
    if (!address.estado.trim()) newErrors.estado = 'Estado é obrigatório';
    if (!address.cep.trim()) {
      newErrors.cep = 'CEP é obrigatório';
    } else if (!/^\d{5}-?\d{3}$/.test(address.cep.replace(/\D/g, '').replace(/(\d{5})(\d{3})/, '$1-$2'))) {
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
      // Preparar itens para o pedido
      const orderItems = cartItems.map(item => ({
        product_id: item.product_id || item.id,
        quantity: item.quantity || 1,
        preco_unitario: item.product?.preco || item.preco,
        titulo: item.product?.titulo || item.titulo,
        imagem_url: item.product?.imagem_url || item.imagem_url,
      }));

      await api.post(`/orders/user/${user.id}`, {
        items: orderItems,
        endereco: address,
      });

      clearCart();
      setShowSuccessModal(true);
    } catch (error) {
      console.error('Erro ao criar pedido:', error);
      showError(error.response?.data?.message || 'Erro de conexão. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  const handleSuccessClose = () => {
    setShowSuccessModal(false);
    navigate('/pedidos');
  };

  const handleInputChange = (field, value) => {
    setAddress(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const formatCEP = (value) => {
    const numbers = value.replace(/\D/g, '');
    if (numbers.length <= 5) return numbers;
    return `${numbers.slice(0, 5)}-${numbers.slice(5, 8)}`;
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(price);
  };

  if (loadingAddress) {
    return (
      <div className="checkout-page">
        <div className="checkout-header">
          <button onClick={() => navigate(-1)} className="back-button-checkout">
            <FiArrowLeft />
          </button>
          <h1>Finalizar Compra</h1>
          <div style={{ width: '40px' }}></div>
        </div>
        <div className="checkout-loading">
          <div className="spinner-checkout"></div>
          <p>Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="checkout-page">
      {/* Header */}
      <div className="checkout-header">
        <button onClick={() => navigate(-1)} className="back-button-checkout">
          <FiArrowLeft />
        </button>
        <h1>Finalizar Compra</h1>
        <div style={{ width: '40px' }}></div>
      </div>

      <div className="checkout-content">
        {/* Resumo do Pedido */}
        <div className="checkout-card summary-card">
          <div className="card-header">
            <FiShoppingCart className="card-icon" />
            <h2>Resumo do Pedido</h2>
          </div>
          <div className="summary-row">
            <span>Itens:</span>
            <span>{cartItems.length}</span>
          </div>
          <div className="summary-row">
            <span>Subtotal:</span>
            <span>{formatPrice(getSubtotal())}</span>
          </div>
          <div className="summary-row">
            <span>Frete:</span>
            <span>{getShippingCost() === 0 ? 'Grátis' : formatPrice(getShippingCost())}</span>
          </div>
          <div className="summary-row total">
            <span>Total:</span>
            <span className="total-value">{formatPrice(total)}</span>
          </div>
        </div>

        {/* Endereço de Entrega */}
        <div className="checkout-card address-card">
          <div className="card-header">
            <FiMapPin className="card-icon" />
            <h2>Endereço de Entrega</h2>
          </div>

          <div className="form-group">
            <label>CEP *</label>
            <input
              type="text"
              className={errors.cep ? 'input-error' : ''}
              value={address.cep}
              onChange={(e) => handleInputChange('cep', formatCEP(e.target.value))}
              onBlur={handleCepBlur}
              placeholder="00000-000"
              maxLength={9}
            />
            {loadingCep && <span className="cep-loading">Buscando...</span>}
            {errors.cep && <span className="error-text">{errors.cep}</span>}
          </div>

          <div className="form-group">
            <label>Rua *</label>
            <input
              type="text"
              className={errors.rua ? 'input-error' : ''}
              value={address.rua}
              onChange={(e) => handleInputChange('rua', e.target.value)}
              placeholder="Nome da rua"
            />
            {errors.rua && <span className="error-text">{errors.rua}</span>}
          </div>

          <div className="form-row">
            <div className="form-group small">
              <label>Número *</label>
              <input
                type="text"
                className={errors.numero ? 'input-error' : ''}
                value={address.numero}
                onChange={(e) => handleInputChange('numero', e.target.value)}
                placeholder="Nº"
              />
              {errors.numero && <span className="error-text">{errors.numero}</span>}
            </div>

            <div className="form-group large">
              <label>Complemento</label>
              <input
                type="text"
                value={address.complemento}
                onChange={(e) => handleInputChange('complemento', e.target.value)}
                placeholder="Apto, bloco, etc."
              />
            </div>
          </div>

          <div className="form-group">
            <label>Bairro *</label>
            <input
              type="text"
              className={errors.bairro ? 'input-error' : ''}
              value={address.bairro}
              onChange={(e) => handleInputChange('bairro', e.target.value)}
              placeholder="Nome do bairro"
            />
            {errors.bairro && <span className="error-text">{errors.bairro}</span>}
          </div>

          <div className="form-row">
            <div className="form-group large">
              <label>Cidade *</label>
              <input
                type="text"
                className={errors.cidade ? 'input-error' : ''}
                value={address.cidade}
                onChange={(e) => handleInputChange('cidade', e.target.value)}
                placeholder="Nome da cidade"
              />
              {errors.cidade && <span className="error-text">{errors.cidade}</span>}
            </div>

            <div className="form-group small">
              <label>Estado *</label>
              <input
                type="text"
                className={errors.estado ? 'input-error' : ''}
                value={address.estado}
                onChange={(e) => handleInputChange('estado', e.target.value.toUpperCase())}
                placeholder="UF"
                maxLength={2}
              />
              {errors.estado && <span className="error-text">{errors.estado}</span>}
            </div>
          </div>
        </div>

        {/* Botão de Confirmar */}
        <button
          className={`checkout-confirm-button ${loading ? 'loading' : ''}`}
          onClick={handleConfirmAddress}
          disabled={loading}
        >
          {loading ? (
            <span className="spinner-checkout-btn"></span>
          ) : (
            <>
              <FiCheck />
              <span>Confirmar Pedido</span>
            </>
          )}
        </button>
      </div>

      {/* Modal de Confirmação */}
      <ConfirmModal
        isOpen={showConfirmModal}
        title="Finalizar Compra"
        message={`Total: ${formatPrice(total)}\n\nDeseja prosseguir com a compra?`}
        confirmText="Confirmar"
        cancelText="Cancelar"
        onConfirm={handleCreateOrder}
        onCancel={() => setShowConfirmModal(false)}
      />

      {/* Modal de Sucesso */}
      {showSuccessModal && (
        <div className="success-modal-overlay" onClick={handleSuccessClose}>
          <div className="success-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="success-icon-container">
              <FiPackage className="success-icon" />
            </div>
            <h2>Pedido Realizado!</h2>
            <p>Seu pedido foi criado com sucesso. Você pode acompanhar o status em "Meus Pedidos".</p>
            <button className="success-button" onClick={handleSuccessClose}>
              Ver Meus Pedidos
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Checkout;
