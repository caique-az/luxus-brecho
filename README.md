# Luxus Brechó 🛍️

Plataforma fullstack de e-commerce de brechó, onde cada produto é uma **peça única**. Um backend Flask serve a API REST consumida por dois clientes independentes: uma loja web (React) e um app mobile (Expo/React Native).

| Camada | Stack |
|--------|-------|
| **Backend** | Python 3.10+ · Flask · MongoDB · JWT · Supabase Storage |
| **Frontend** | React 19 · Vite 6 · Zustand · Zod · Vitest |
| **Mobile** | Expo 49 · React Native · TypeScript · Expo Router · NativeWind |

## Visão geral

```
luxus-brecho/
├─ backend/    API Flask + MongoDB — fonte única de verdade
├─ frontend/   Loja web (SPA) + painel administrativo
├─ mobile/     App da loja para Android/iOS
└─ docs/       Documentação técnica
```

O backend concentra toda a regra de negócio e autenticação; web e mobile são clientes que conversam apenas com o contrato da API. Entenda o desenho completo em **[docs/arquitetura.md](./docs/arquitetura.md)**.

## Início rápido

```bash
# Backend
cd backend && pip install -r requirements.txt
cp .env.example .env          # configure as variáveis
python run.py                 # http://localhost:5000/api

# Frontend
cd frontend && npm install
npm run dev                   # http://localhost:5173

# Mobile (na raiz, primeiro sincronize o IP da rede)
npm run dev                   # gera network-config.json
cd mobile && npx expo start --clear
```

Para subir backend + frontend de uma vez, na raiz: `npm run dev:full`.

## Funcionalidades

- **Autenticação JWT** com access + refresh token e confirmação de email
- **Catálogo** de produtos com filtros, busca textual e paginação
- **Carrinho** de peças únicas (sem quantidade por item)
- **Favoritos** sincronizados com o backend
- **Pedidos** com endereço de entrega e notificação de status por email
- **Painel admin** para gestão de produtos (role-based)

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| 🏛️ [Arquitetura](./docs/arquitetura.md) | Diagramas, camadas, modelo de dados, autenticação |
| 📡 [Referência da API](./docs/api-reference.md) | Todos os endpoints REST |
| ⚙️ [Setup e Deploy](./docs/setup-e-deploy.md) | Ambiente local, variáveis, rede mobile, deploy |
| 📐 [Convenções](./docs/convencoes.md) | Padrões de código, testes e Git |

Cada subprojeto também tem seu próprio README (`backend/`, `frontend/`, `mobile/`) com detalhes específicos.

## Testes

```bash
cd backend && pytest
cd frontend && npm test
cd mobile && npm test
```

## Licença

MIT. Projeto desenvolvido também para fins de aprendizado.
