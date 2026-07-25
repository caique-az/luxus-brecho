# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

Monorepo de e-commerce de brechó com três aplicações independentes que compartilham a mesma API:

- **`backend/`** — API REST em Flask + MongoDB, autenticação JWT, Supabase Storage (imagens) e SMTP (emails).
- **`frontend/`** — SPA em React 19 + Vite 6, estado com Zustand, testes com Vitest.
- **`mobile/`** — App Expo 49 / React Native + TypeScript, roteamento com Expo Router, estilização com NativeWind, testes com Jest.

Cada subprojeto tem seu próprio gerenciamento de dependências (`pip` no backend, `npm` no frontend/mobile) e seu próprio README. O `package.json` da raiz contém apenas scripts orquestradores — não há dependências instaladas nele.

## Comandos

### Raiz (orquestração)
```bash
npm run dev            # sync-network.js: gera network-config.json (opcional — cada app detecta o IP sozinho)
npm run dev:full       # start-dev.js: sobe backend + frontend juntos
npm run backend        # cd backend && python run.py
npm run frontend       # cd frontend && npm run dev
npm run mobile         # cd mobile && npx expo start --clear
```

### Backend (`cd backend`)
```bash
pip install -r requirements.txt
python run.py          # API em http://localhost:5000/api
pytest                 # roda todos os testes (config em pytest.ini, -v --tb=short)
pytest tests/test_products.py            # um arquivo
pytest tests/test_products.py::test_nome # um teste específico
```

### Frontend (`cd frontend`)
```bash
npm run dev            # Vite dev server em http://localhost:5173
npm run build          # build de produção
npm run lint           # eslint .
npm test               # vitest (watch)
npm run test:coverage  # vitest run --coverage
npx vitest run src/store/cartStore.test.js   # um arquivo de teste
```

### Mobile (`cd mobile`)
```bash
npm install
npx expo start --clear # Metro bundler + QR code para Expo Go
npm run lint           # eslint . --ext .js,.jsx,.ts,.tsx
npm test               # jest
npm run reset          # apaga node_modules + .expo e reinstala
```

## Arquitetura

### Backend — camadas (app factory + blueprints)
`create_app()` em `app/__init__.py` é o ponto central: configura CORS, rate limiting, compressão gzip, conecta ao MongoDB e **chama `ensure_*` de cada model para garantir coleções/índices no startup**. Os blueprints são registrados a partir de uma lista declarativa `blueprints_to_register` (cada falha de import é tolerada, não derruba o app).

Fluxo por requisição, separado em três camadas dentro de `app/`:
- **`routes/`** — blueprints Flask, definem URL + método e aplicam decorators de auth.
- **`controllers/`** — lógica de negócio; recebem `request`, validam e respondem JSON.
- **`models/`** — acesso ao MongoDB e função `ensure_*_collection`/`ensure_indexes`.
- **`services/`** — `jwt_service` (gera/valida tokens, decorators `@jwt_required` e `@admin_required`), `email_service` (SMTP), `supabase_storage` (upload de imagens).

Convenções importantes:
- Respostas JSON seguem o padrão `{ "success": bool, "message": str, ... }`.
- `app.url_map.strict_slashes = False` — não confie em barra final para roteamento.
- `app.db` pode ser `None` quando `MONGODB_URI` não está configurado; o app sobe mesmo sem banco.
- `run.py` obtém host/porta/IP de `app/utils/network.py`: env vars (`FLASK_HOST`/`FLASK_PORT`) têm precedência sobre `network-config.json`, e o IP da rede é detectado em tempo de execução. Usa `use_reloader=False` propositalmente para evitar `WinError 10038` no Windows.
- Auth via header `Authorization: Bearer <token>`, com access + refresh token.

### Frontend — SPA React por features
- **`src/pages/<Pagina>/index.jsx` + `index.css`** — cada rota é uma pasta com componente e CSS co-localizados (nomes em português, ex.: `Carrinho`, `Favoritos`, `ProdutoDetalhes`). Páginas admin em `src/pages/Admin/`.
- **`src/store/`** — stores Zustand (`authStore`, `cartStore`, `favoritesStore`). O `authStore` orquestra efeitos colaterais (ex.: ao logar, dispara `useFavoritesStore.loadFavorites()`).
- **`src/services/`** — `api.js` é uma instância axios única com interceptors: injeta o Bearer token (exceto em rotas de auth) e faz **refresh automático de token em 401**, com fila (`failedQueue`) para não disparar refresh concorrente. Os demais arquivos (`products`, `auth`, `orders`, ...) são wrappers por domínio sobre essa instância.
- Base da API: `src/services/apiConfig.js` é a fonte única (`API_BASE_URL` e `API_URL`). Usa `VITE_API_URL` quando definida (aceita com ou sem `/api`); em dev sem a variável, deriva de `window.location.hostname` na porta `VITE_API_PORT` (default 5000) — abrir o Vite pelo IP da rede faz a API seguir o mesmo host.

### Mobile — Expo Router + camada de config de rede
- **`app/`** — roteamento por arquivos do Expo Router. `(tabs)/` é o grupo de abas; rotas dinâmicas como `product/[id].tsx`; `admin/` para telas de gestão.
- **`constants/config.ts`** — objeto `CONFIG` central, todo configurável por env vars `EXPO_PUBLIC_*`. `getApiUrl()` decide a URL: em produção usa `PRODUCTION_URL`, em dev usa `NETWORK_URL`, que é derivada do host do dev server (`Constants.expoConfig.hostUri`) na porta `EXPO_PUBLIC_API_PORT` (default 5000).
- **`services/api.ts`** — `ApiService` com timeout, retry/backoff e cache local (AsyncStorage via `cacheManager`) para GETs.
- **`schemas/`** — validação Zod; `hooks/useZodForm.ts` integra com react-hook-form.

## Configuração de rede entre dispositivos

Para testar em um dispositivo físico na mesma Wi-Fi, cada app descobre o endereço da API por conta própria — **não é preciso rodar nada na raiz antes**:

- **Backend** — `app/utils/network.py` detecta o IP da máquina em tempo de execução (socket UDP consultando a tabela de rotas, sem enviar pacote). `resolve_server_config()` serve `run.py`; `get_base_url()` serve os links de e-mail.
- **Mobile** — `constants/config.ts` deriva a URL do host do dev server (`Constants.expoConfig.hostUri`): o Metro roda na mesma máquina que o backend, então o IP que baixou o bundle é o IP da API. Sobrevive a troca de rede sem `--clear`.
- **Frontend** — `src/services/apiConfig.js` deriva de `window.location.hostname`; o Vite escuta em todas as interfaces (`server.host: true`), então abrir `http://<ip>:5173` no celular já aponta a API para o mesmo IP.

Casos especiais: emulador Android cai para `10.0.2.2` (o `hostUri` reporta `localhost` via `adb reverse`) e `expo start --tunnel` exige `EXPO_PUBLIC_NETWORK_URL`. Racional em `docs/decisions.md` (ADR-0001).

`network-config.json` (gerado por `npm run dev`, não versionado) virou **override opcional**: o backend ainda respeita `host`/`port` dele, e o mobile usa `mobile.api_urls` como fallback quando não há dev server. Para forçar endereços manualmente, prefira as env vars (`FLASK_HOST`/`FLASK_PORT`, `VITE_API_URL`, `EXPO_PUBLIC_NETWORK_URL`).

## Variáveis de ambiente

- **Backend** (`backend/.env`, ver `.env.example`): `MONGODB_URI`, `MONGODB_DATABASE`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `FLASK_DEBUG`, `FRONTEND_ORIGIN` (lista CSV de origens CORS), `SUPABASE_URL`/`SUPABASE_KEY`/`SUPABASE_BUCKET`, e bloco `SMTP_*` para emails.
- **Frontend**: `VITE_API_URL` (obrigatória em produção), `VITE_API_PORT` (default 5000, usada na derivação em dev).
- **Mobile**: prefixo `EXPO_PUBLIC_*` (ex.: `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_PRODUCTION_URL`, `EXPO_PUBLIC_API_PORT`).

## Regras de domínio

- Cada produto é uma **peça única**: o carrinho não tem quantidade por item — um produto está ou não no carrinho.
- Frete e limite de frete grátis são configuráveis no mobile via `CONFIG.CART`.
