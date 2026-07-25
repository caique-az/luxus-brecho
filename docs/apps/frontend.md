# Frontend web — estado interno

> Fonte: `frontend/src/` · `frontend/package.json`
> Contrato da API: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md#débitos-do-frontend-web)

SPA da loja + painel admin. Stack: **React ^19.1**, **Vite ^6.3**, **react-router-dom ^7.6**, **Zustand ^4.5**, **Zod ^4.1**, **axios ^1.11**; testes com **Vitest ^3.2** e E2E com Robot Framework.

Estado de alinhamento com o backend: **majoritariamente alinhado** (JWT com refresh, carrinho de peça única, exclusão de conta com Authorization), com dois resíduos conhecidos — [FE-01](../alinhamento-e-debitos.md#fe-01) (X-User-Id legado em favoritos) e [FE-03](../alinhamento-e-debitos.md#fe-03) (resíduo de `quantity` no payload do Checkout).

## Rotas e páginas

Rotas registradas em `src/App.jsx` (tudo dentro de um único `<Layout>`; `App` chama `authStore.initialize()` no mount):

- **Loja/públicas:** `/` (Home), `sobre`, `produtos`, `produto/:id`, `categorias`, `suporte`, `contato`, `carrinho`, `favoritos`, `login`, `registro`, `esqueci-senha`, `redefinir-senha/:token`, `reenviar-confirmacao`, `perfil`, `checkout`, `pedidos`.
- **Configurações:** `configuracoes`, `configuracoes/endereco`, `configuracoes/senha`, `configuracoes/email`, `configuracoes/excluir`, `configuracoes/excluir/codigo`, `conta-excluida`.
- **Admin:** `admin/registro`, `admin/products`, `admin/products/new`, `admin/products/edit/:id`.

Cada página é uma pasta `src/pages/<Pagina>/` com `index.jsx` + `index.css` co-localizados (nomes em português). **Não há `ProtectedRoute` nem guarda de role no router** — a proteção é feita dentro de cada página (ex.: `useEffect` que redireciona para `/login`).

## Stores Zustand (`src/store/`)

| Store | Estado/ações | Observações |
|-------|--------------|-------------|
| `authStore` | `user`, `isAuthenticated`; `login`, `register`, `logout`, `initialize`, `updateUser` | Orquestra efeitos cruzados: `login`/`initialize` disparam `favoritesStore.loadFavorites()`; `logout` limpa favoritos e o cache (`cacheManager.invalidateAll()`) |
| `cartStore` | `cart[]`; `addToCart`, `removeFromCart`, `clearCart`, getters | **Peça única, sem `quantity`**: `addToCart` bloqueia duplicados; `getSubtotal` soma `item.preco` sem multiplicar; frete R$ 15 com grátis ≥ R$ 150; persistência em `localStorage['luxus-cart']`. Independente do authStore. |
| `favoritesStore` | `favorites[]`; `loadFavorites`, `toggleFavorite`, ... | Cache de 30s + deduplicação de requisições concorrentes (`fetchPromise`/`lastFetchTime`); delega para `favoritesService` |

## Camada de API (`src/services/`)

**`apiConfig.js`** — fonte única da URL da API, consumida por `api.js` e `auth.js`. `VITE_API_URL` vence quando definida (normalizada: aceita com ou sem `/api`); em dev sem a variável, deriva de `window.location.hostname` na porta `VITE_API_PORT` (default 5000). Exporta `API_BASE_URL` (sem sufixo) e `API_URL` (com `/api`).

**`api.js`** — instância axios única com `baseURL = API_URL`, timeout 10s.

- Interceptor de **request**: injeta `Authorization: Bearer <accessToken>` em tudo, exceto nas rotas de auth (`/users/auth`, `/users/refresh-token`, `/users/forgot-password`, `/users/reset-password`).
- Interceptor de **response**: em 401, faz **refresh automático** com flag `isRefreshing` + fila `failedQueue` (evita refresh concorrente; requisições em espera são repetidas com o token novo). Se o refresh falha: `logout()` + redirect para `/login`.

Wrappers por domínio: `products.js`, `categories.js`, `orders.js`, `favorites.js` (usam a instância `api`), `cep.js` (ViaCEP) e `auth.js` — este último usa **`fetch` cru** (não o axios) e gerencia os tokens no localStorage (`luxus_access_token`, `luxus_refresh_token`, `luxus_token_expires`, `luxus_user`).

Pontos que fogem do padrão (registrados como débito):

- `favorites.js` ainda monta o header `X-User-Id` manualmente em cada chamada — redundante, o Bearer vai junto ([FE-01](../alinhamento-e-debitos.md#fe-01)).
- `pages/Checkout/index.jsx` já usa a instância axios (`api.get`/`api.post`, com Bearer), mas ainda monta `quantity: item.quantity || 1` no item do pedido — campo que o store não tem e o backend ignora ([FE-03](../alinhamento-e-debitos.md#fe-03)).

## Componentes e utilitários

`src/components/`: `Header` (nav + busca com `SearchSchema` Zod + badge do carrinho), `Footer`, `Layout` (Header + `<Outlet/>` + Footer), `ConfirmModal`, `LogoutModal`, `Skeleton`, `Toast`/`ToastContainer`. Contexto `ToastContext`; hooks `useDebounce`, `useToast`; utils `cache.js`, `logger.js`.

## Testes

- **Vitest**: `src/services/auth.test.js` (tokens, expiração, login incl. e-mail não confirmado) e `src/store/cartStore.test.js` (peça única, duplicados, frete, totais). `npm test` (watch) / `npm run test:coverage`.
- **E2E** (Robot Framework + Selenium): `frontend/test/*.robot` (homepage, botões, Sobre nós).
