# Mobile — estado interno

> Fonte: `mobile/app/` · `mobile/services/` · `mobile/store/` · `mobile/constants/` · `mobile/package.json`
> Contrato da API: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md#débitos-do-mobile)

App da loja em **Expo ^49** (expo-router ^2, React Native 0.72), TypeScript, NativeWind ^2, Zustand ^5, Zod ^3, AsyncStorage.

**Este é o app mais defasado em relação ao backend.** Em resumo: não implementa JWT, favoritos e exclusão de conta usam o esquema legado removido do backend (ambos **quebrados**), o carrinho ainda modela `quantity`, e não existe fluxo de checkout funcional. A lista completa: [débitos do mobile](../alinhamento-e-debitos.md#débitos-do-mobile).

## Autenticação — estado real

**Não há JWT** ([MB-01](../alinhamento-e-debitos.md#mb-01)): o `authService.login` (`services/auth.ts`) apenas grava a flag `'authenticated'` e o `user_data` no AsyncStorage; `isAuthenticated()` só checa a flag. Não existe nenhuma ocorrência de `Authorization`/`Bearer` no código do mobile — nem refresh, nem expiração.

Consequências práticas contra o backend atual:

- **Favoritos** (`services/favorites.ts`): `fetchWithUserId` injeta o header `X-User-Id` lido do AsyncStorage — o backend removeu esse esquema; todas as chamadas respondem 401 ([MB-02](../alinhamento-e-debitos.md#mb-02)).
- **Exclusão de conta** (`services/auth.ts:239-273`): envia `user_id` no corpo, sem token — 401 ([MB-03](../alinhamento-e-debitos.md#mb-03)).
- Qualquer rota protegida por posse (carrinho, pedidos) responde 401 para o app.

## Rotas (Expo Router, `app/`)

- Raiz `_layout.tsx`: `Stack` sem header, envolto em `ToastProvider`.
- Grupo de abas `(tabs)/`: `index` (Home), `favorites`, `products`, `cart`, `menu`.
- Dinâmicas: `product/[id].tsx`, `category/[id].tsx`, `admin/edit-product/[id].tsx`.
- Admin: `admin/create-product.tsx`, `admin/manage-products.tsx`.
- Demais telas: `login`, `register`, `register-admin`, `forgot-password`, `resend-confirmation`, `profile`, `account-settings`, `settings/{address,password,email,delete}`, `delete-account-code`, `account-deleted`, `categories`, `search`, `orders`, `order-history`, `checkout`, `contact`, `support`, `+not-found`.

**Checkout órfão** ([MB-05](../alinhamento-e-debitos.md#mb-05)): o botão "Finalizar Compra" da aba carrinho (`app/(tabs)/cart.tsx:305-321`) só exibe um `Alert` e limpa o carrinho — não navega para `checkout.tsx`, que fica inalcançável no fluxo normal.

## Carrinho — ainda com `quantity`

`store/cartStore.ts` diverge da regra de peça única ([MB-04](../alinhamento-e-debitos.md#mb-04)): a interface `CartItem` tem `quantity` (linha 13), `getSubtotal` multiplica `preco * quantity` (linha 46), existe `updateQuantity` (linhas 131-151) e o `syncWithServer` envia `{product_id, quantity}` (linhas 192-201). Os comentários dizem "peça única / sempre 1", mas o modelo de dados carrega o campo. Persistência local em `AsyncStorage['luxus_cart']`; frete e limite de frete grátis configuráveis via `CONFIG.CART` (R$ 15 / R$ 150).

## Camada de API e configuração

**`services/api.ts`** (`ApiService`, singleton) — `fetch` + `AbortController`:

- timeout `CONFIG.API.TIMEOUT` (10s); retry 2× com backoff exponencial (base 2s) para timeout/erros ≥ 500;
- **cache** de GETs via `cacheManager` (AsyncStorage): produtos 2 min, resumo de categorias 5 min; invalidado nas mutações de produto;
- **não injeta Authorization** em nenhuma requisição;
- cobre produtos, categorias, imagens e health/testConnection.

**`constants/config.ts`** — objeto `CONFIG` com tudo configurável por `EXPO_PUBLIC_*` (API, NETWORK, CART, PAGINATION, CATEGORIES, APP, DEBUG). Em dev, faz `require('../network-config.json')` para descobrir a `NETWORK_URL` (gerado por `npm run dev` na raiz).

**`getApiUrl()` existe duplicada** ([MB-06](../alinhamento-e-debitos.md#mb-06)): em `constants/config.ts` (não usada pelos services) e em `utils/networkUtils.ts` — **esta é a efetivamente importada** por api/auth/favorites/stores/telas. Ambas: produção → `PRODUCTION_URL`; dev → `NETWORK_URL`.

## Schemas e hooks

- `schemas/auth.schema.ts` (`LoginSchema`, `RegisterSchema` com política de senha letra+número, `SearchSchema`, helper `useZodValidation`) e `schemas/createProduct.schema.ts` (`CreateProductFormSchema`, `EditProductSchema`, `categoryOptions`).
- `hooks/useProducts.ts` (`useProducts`, `useFeaturedProducts`, `useTopSellingProducts`, `useProductSearch`), `hooks/useZodForm.ts` (react-hook-form + Zod), `hooks/useNetworkStatus.ts` (netinfo).

## Testes

**Não há nenhuma suíte** ([MB-07](../alinhamento-e-debitos.md#mb-07)): `jest.config.js` existe, mas `npm test` não encontra testes; `mobile/tests/` contém apenas `requirements.txt` e `robot/resources/config.robot` (sem suites Robot).
