import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import api from '../../services/api';
import { 
  FiArrowLeft, 
  FiPackage, 
  FiMapPin, 
  FiClock,
  FiCheckCircle,
  FiTruck,
  FiXCircle,
  FiShoppingBag,
  FiLogIn
} from 'react-icons/fi';
import './index.css';

const STATUS_CONFIG = {
  pendente: { label: 'Pendente', color: '#F59E0B', icon: FiClock, bg: '#FEF3C7' },
  confirmado: { label: 'Confirmado', color: '#3B82F6', icon: FiCheckCircle, bg: '#DBEAFE' },
  em_preparacao: { label: 'Em Preparação', color: '#8B5CF6', icon: FiPackage, bg: '#EDE9FE' },
  enviado: { label: 'Enviado', color: '#06B6D4', icon: FiTruck, bg: '#CFFAFE' },
  entregue: { label: 'Entregue', color: '#22C55E', icon: FiCheckCircle, bg: '#D1FAE5' },
  cancelado: { label: 'Cancelado', color: '#EF4444', icon: FiXCircle, bg: '#FEE2E2' },
};

const Pedidos = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, initialize } = useAuthStore();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (isAuthenticated && user) {
      fetchOrders();
    } else {
      setLoading(false);
    }
  }, [isAuthenticated, user]);

  const fetchOrders = async () => {
    if (!user) return;

    try {
      const { data } = await api.get(`/orders/user/${user.id}`);
      setOrders(data.orders || []);
    } catch (error) {
      console.error('Erro ao buscar pedidos:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(price);
  };

  // Não autenticado
  if (!isAuthenticated) {
    return (
      <div className="pedidos-page">
        <div className="pedidos-header">
          <button onClick={() => navigate(-1)} className="back-button-pedidos">
            <FiArrowLeft />
          </button>
          <h1>Meus Pedidos</h1>
          <div style={{ width: '40px' }}></div>
        </div>

        <div className="pedidos-empty">
          <FiLogIn className="empty-icon" />
          <h2>Faça login para ver seus pedidos</h2>
          <p>Entre na sua conta para acessar seu histórico de pedidos.</p>
          <Link to="/login" className="pedidos-login-btn">
            <FiLogIn />
            <span>Fazer Login</span>
          </Link>
        </div>
      </div>
    );
  }

  // Loading
  if (loading) {
    return (
      <div className="pedidos-page">
        <div className="pedidos-header">
          <button onClick={() => navigate(-1)} className="back-button-pedidos">
            <FiArrowLeft />
          </button>
          <h1>Meus Pedidos</h1>
          <div style={{ width: '40px' }}></div>
        </div>

        <div className="pedidos-loading">
          <div className="spinner-pedidos"></div>
          <p>Carregando pedidos...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pedidos-page">
      {/* Header */}
      <div className="pedidos-header">
        <button onClick={() => navigate(-1)} className="back-button-pedidos">
          <FiArrowLeft />
        </button>
        <h1>Meus Pedidos</h1>
        <div style={{ width: '40px' }}></div>
      </div>

      <div className="pedidos-content">
        {orders.length === 0 ? (
          <div className="pedidos-empty">
            <FiPackage className="empty-icon" />
            <h2>Nenhum pedido realizado</h2>
            <p>Você ainda não fez nenhum pedido. Explore nossos produtos!</p>
            <Link to="/produtos" className="pedidos-shop-btn">
              <FiShoppingBag />
              <span>Ver Produtos</span>
            </Link>
          </div>
        ) : (
          <div className="pedidos-list">
            {orders.map((order) => {
              const statusConfig = STATUS_CONFIG[order.status] || STATUS_CONFIG.pendente;
              const StatusIcon = statusConfig.icon;
              
              return (
                <div key={order.id} className="pedido-card">
                  {/* Header do Pedido */}
                  <div className="pedido-header">
                    <div className="pedido-info">
                      <h3>Pedido #{order.id}</h3>
                      <span className="pedido-date">{formatDate(order.created_at)}</span>
                    </div>
                    <div 
                      className="pedido-status"
                      style={{ 
                        backgroundColor: statusConfig.bg,
                        color: statusConfig.color 
                      }}
                    >
                      <StatusIcon size={14} />
                      <span>{statusConfig.label}</span>
                    </div>
                  </div>

                  {/* Itens do Pedido */}
                  <div className="pedido-items">
                    {order.items.slice(0, 2).map((item, index) => (
                      <div key={index} className="pedido-item">
                        <img
                          src={item.imagem_url || 'https://via.placeholder.com/50'}
                          alt={item.titulo}
                          className="item-image"
                        />
                        <div className="item-info">
                          <span className="item-title">{item.titulo}</span>
                          <span className="item-price">
                            {formatPrice(item.preco_unitario)}
                          </span>
                        </div>
                      </div>
                    ))}
                    {order.items.length > 2 && (
                      <span className="more-items">
                        +{order.items.length - 2} item(s)
                      </span>
                    )}
                  </div>

                  {/* Endereço */}
                  <div className="pedido-address">
                    <FiMapPin size={14} />
                    <span>
                      {order.endereco.rua}, {order.endereco.numero} - {order.endereco.bairro}
                    </span>
                  </div>

                  {/* Footer do Pedido */}
                  <div className="pedido-footer">
                    <span className="total-label">Total:</span>
                    <span className="total-value">{formatPrice(order.total)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default Pedidos;
