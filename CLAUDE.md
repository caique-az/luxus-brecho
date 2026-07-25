# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

Monorepo de e-commerce de brechó com três aplicações independentes que compartilham a mesma API:

- **`backend/`** — API REST em Flask + MongoDB, autenticação JWT, Supabase Storage (imagens) e SMTP (emails). Fonte única da regra de negócio.
- **`frontend/`** — SPA em React 19 + Vite 6, estado com Zustand, testes com Vitest.
- **`mobile/`** — App Expo 49 / React Native 0.72 + TypeScript, roteamento com Expo Router, estilização com NativeWind, testes com Jest.

Web e mobile são **clientes** do contrato da API — não replicam regra de negócio. Cada subprojeto tem seu próprio gerenciamento de dependências (`pip` no backend, `npm` no frontend/mobile) e seu próprio README. O `package.json` da raiz contém apenas scripts orquestradores — não há dependências instaladas nele.

## Relação com `docs/`

`docs/` é a documentação normativa (para humanos); este arquivo é o guia operacional do agente. Por convenção do projeto, **sobreposição se resolve com link, não com cópia** — não duplique aqui conteúdo de `docs/`.

Antes de mexer em algo não trivial, consulte:

| Documento | Quando |
|-----------|--------|
| [docs/alinhamento-e-debitos.md](./docs/alinhamento-e-debitos.md) | **Leia sempre antes de "consertar" uma inconsistência** — matriz Backend×Web×Mobile e todos os débitos com ID (`BE-*`, `FE-*`, `MB-*`, `CI-*`, `DOC-*`). Muita divergência é conhecida e deliberada. |
| [docs/convencoes.md](./docs/convencoes.md) | Padrões de código, API, auth, testes, Git e documentação |
| [docs/api-reference.md](./docs/api-reference.md) + `docs/api/` | Contrato da API (um doc por blueprint) |
| [docs/arquitetura.md](./docs/arquitetura.md) | Camadas, modelo de dados, boot |
| [docs/setup-e-deploy.md](./docs/setup-e-deploy.md) | Tabela canônica de env vars, rede do mobile, deploy |

Regras de documentação que afetam o trabalho de código:
- **Realidade > intenção** — documenta-se o comportamento observável, mesmo indesejado. O estado ideal vira débito registrado.
- **Mudou o contrato, muda a doc no mesmo PR** — alterou rota, decorator ou shape de resposta → toque o `docs/api/*.md` correspondente (e a matriz, se afetar clientes).
- **Débito não se apaga — se resolve**: item resolvido migra para a seção "Resolvidos" com data e hash do commit.

## Comandos

### Raiz (orquestração)
```bash
npm run dev            # sync-network.js: detecta o IP da rede e gera network-config.json
npm run dev:full       # start-dev.js: sobe backend + MOBILE (não inclui o frontend web)
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
npm test               # jest — configurado, mas NÃO há suítes hoje (MB-07)
npm run reset          # apaga node_modules + .expo e reinstala
```

## Arquitetura

### Backend — camadas (app factory + blueprints)
`create_app()` em `app/__init__.py` é o ponto central: configura CORS, rate limiting, compressão gzip, conecta ao MongoDB e **chama `ensure_*` de cada model para garantir coleções/índices no startup**. Os blueprints vêm de uma lista declarativa `blueprints_to_register`; **todos são obrigatórios — uma falha de import levanta `RuntimeError` e derruba o boot** (proposital: evita API mutilada respondendo 404 em silêncio).

Fluxo por requisição, separado em três camadas dentro de `app/`:
- **`routes/`** — blueprints Flask, definem URL + método e aplicam decorators de auth.
- **`controllers/`** — lógica de negócio; recebem `request`, validam e respondem JSON.
- **`models/`** — acesso ao MongoDB, validação da entidade (`validate_*`, `normalize_*`, `prepare_new_*`) e `ensure_*_collection`/`ensure_indexes`.
- **`services/`** — `jwt_service` (gera/valida tokens; decorators `@jwt_required`, `@jwt_optional`, `@admin_required`, `@owner_or_admin_required`), `email_service` (SMTP), `supabase_storage` (upload de imagens).
- **`utils/`** — helpers canônicos, **reuse em vez de reimplementar**: `responses.ok/err` (envelope), `db.require_db` (guard de banco → 503), `serialization.serialize_doc` (remove `_id`), `pagination.parse_pagination` (clamp de `page`/`page_size`), `counters.next_sequence` (ids sequenciais), `cache.py` (cache de categorias).

**Exceção conhecida:** `products` não tem controller — `routes/products_routes.py` (~370 linhas) concentra schema Marshmallow, regra e acesso ao model. É o único recurso fora do padrão; ao criar um recurso novo, siga as três camadas (rota fina → controller → model) e não replique esse desenho.

Convenções importantes:
- **Envelope de resposta único e plano**, montado pelos helpers `ok()`/`err()` de `utils/responses.py` — **nunca `jsonify` cru** em controller ou rota nova. Sucesso: `{"success": true, "message"?, <chaves de domínio no topo>}`; erro: `{"success": false, "message": str, "errors"?: {campo: motivo}}`. Os dados **não** ficam aninhados sob `data`. A chave `error` foi abolida — erro usa `message`. Exceção documentada: listas puras (`/categories/summary`) não passam pelos helpers. Contrato travado em `tests/test_envelope.py`.
- **Toda env var passa por `app/config.py`** — uma função por variável, concentrando nome, default e parsing; nenhum módulo lê `os.environ` direto. São funções, não constantes, para que os testes possam usar `monkeypatch.setenv`. Valor numérico inválido avisa e cai no default. Exceção deliberada: `JWT_SECRET_KEY` é lida no import de `jwt_service.py`, para que a ausência derrube o startup e não a primeira requisição autenticada.
- IDs são **inteiros sequenciais** da coleção de contadores (`utils/counters.next_sequence`, exposto por cada model como `get_next_id`/`get_next_sequence`), não `ObjectId`. O `_id` do Mongo nunca vaza na resposta.
- **Paginação sempre por `utils/pagination.parse_pagination`** — não releia `page`/`page_size` à mão. O `int()` cru sobre a query string já causou 500 em três rotas (BE-08); o helper cai no default e faz o clamp.
- Índices/schema são garantidos em código via `ensure_*()` no `create_app()` — **não** crie índices manualmente no banco.
- `app.url_map.strict_slashes = False` — não confie em barra final para roteamento.
- `app.db` pode ser `None` quando `MONGODB_URI` não está configurado; o app sobe mesmo sem banco (daí `@require_db`).
- `run.py` lê `network-config.json` da raiz (se existir) para host/porta/IP; caso contrário usa env vars. Usa `use_reloader=False` propositalmente para evitar `WinError 10038` no Windows.
- **O backend roda em Vercel serverless** em produção (`@vercel/python` sobre `index.py`). O processo é congelado quando a resposta sai — trabalho em `threading.Thread` depois do `return` não tem garantia de completar. É por isso que o envio de e-mail segue síncrono (BE-09).

### Autenticação — um único esquema
JWT via header `Authorization: Bearer <token>`, com access + refresh token. A identidade autenticada vem de **`g.user_id` (int)** — nunca de um id no corpo da requisição ou header customizado. O antigo `X-User-Id` foi removido do backend por ser falsificável; onde ele ainda aparece nos clientes é débito (`FE-01`, `MB-02`), não contrato.

### Frontend — SPA React por features
- **`src/pages/<Pagina>/index.jsx` + `index.css`** — cada rota é uma pasta com componente e CSS co-localizados (nomes em português, ex.: `Carrinho`, `Favoritos`, `ProdutoDetalhes`). Páginas admin em `src/pages/Admin/`.
- **`src/store/`** — stores Zustand (`authStore`, `cartStore`, `favoritesStore`). O `authStore` orquestra efeitos colaterais (ex.: ao logar, dispara `useFavoritesStore.loadFavorites()`).
- **`src/services/`** — `api.js` é uma instância axios única com interceptors: injeta o Bearer token (exceto em rotas de auth) e faz **refresh automático em 401**, com fila (`failedQueue`) para não disparar refresh concorrente. Os demais arquivos (`products`, `auth`, `orders`, ...) são wrappers por domínio sobre essa instância — **nunca crie outra instância axios**, ela é quem injeta o token.
- Base da API: `import.meta.env.VITE_API_URL` (fallback `http://127.0.0.1:5000`), com `/api` anexado.

### Mobile — Expo Router + camada de config de rede
- **`app/`** — roteamento por arquivos do Expo Router. `(tabs)/` é o grupo de abas; rotas dinâmicas como `product/[id].tsx`; `admin/` para telas de gestão.
- **`constants/config.ts`** — objeto `CONFIG` central (timeouts, cache, frete). **As env vars `EXPO_PUBLIC_*` dele não funcionam** ([MB-09](./docs/alinhamento-e-debitos.md#mb-09)): os helpers leem `process.env[key]` dinâmico e o Metro só inlina acesso por ponto, então tudo cai no fallback. Não confie no `.env` do mobile até isso ser corrigido.
- **`utils/networkUtils.ts`** — `getApiUrl()` decide a URL: em produção usa `PRODUCTION_URL`, em dev usa `NETWORK_URL`. É a única — existia uma cópia em `config.ts` que ninguém importava (MB-06).
- **`services/api.ts`** — `ApiService` com timeout, retry/backoff e cache local (AsyncStorage via `cacheManager`) para GETs.
- **`schemas/`** — validação Zod; `hooks/useZodForm.ts` integra com react-hook-form.

**O mobile já usa JWT real** (armazena tokens no AsyncStorage, injeta `Authorization: Bearer` via `getAuthHeaders`, renova em 401) e o build Android voltou a compilar. Mas ainda está defasado em pontos que valem checar nos débitos `MB-*` antes de mexer: o carrinho modela `quantity` embora o backend seja peça única (MB-04), o checkout existe mas está fora do fluxo principal (MB-05), `getApiUrl()` está duplicada e a versão importada é a de `utils/networkUtils.ts` (MB-06), favoritos ainda anexam um `X-User-Id` legado que o backend ignora (MB-02), e não há **nenhuma** suíte de testes apesar do `jest.config.js` (MB-07).

## Configuração de rede entre dispositivos (importante)

Para testar o mobile em um dispositivo físico na mesma Wi-Fi, o IP da máquina precisa ser propagado para backend e mobile. O fluxo é:

1. `npm run dev` na raiz roda `sync-network.js`, que detecta o IPv4 da rede (`ipconfig`/`ifconfig`) e escreve `network-config.json` na raiz **e** em `mobile/network-config.json`.
2. O backend (`run.py`) lê esse arquivo para escolher host/porta/IP.
3. O mobile (`constants/config.ts`) faz `require('../network-config.json')` em dev para descobrir a `NETWORK_URL`.

`network-config.json` é gerado (não versionado); use `network-config.example.json` como referência. Se mudar de rede, rode `npm run dev` de novo e reinicie o Metro com `--clear`.

## Variáveis de ambiente

Tabela canônica em [docs/setup-e-deploy.md](./docs/setup-e-deploy.md). Resumo:

- **Backend** (`backend/.env`, ver `.env.example`): `JWT_SECRET_KEY` (**obrigatória** — sem ela o app não sobe), `MONGODB_URI`, `MONGODB_DATABASE`, `FLASK_DEBUG`, `FRONTEND_ORIGIN` (lista CSV de origens CORS), `ADMIN_EMAIL`/`ADMIN_PASSWORD` (semeiam o 1º admin; sem elas, nenhum admin é criado), `SUPABASE_URL`/`SUPABASE_KEY`/`SUPABASE_BUCKET`, e bloco `SMTP_*` para emails. Nomes e defaults vivem em `app/config.py`.
- **Frontend**: `VITE_API_URL`.
- **Mobile**: prefixo `EXPO_PUBLIC_*` (ex.: `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_PRODUCTION_URL`) — **hoje sem efeito**, ver MB-09.

Os prefixos importam: sem `VITE_*` / `EXPO_PUBLIC_*` a variável não é embarcada no bundle. E, no Expo, o prefixo não basta — o acesso precisa ser estático (`process.env.EXPO_PUBLIC_X`, literal), porque o inline é feito por regex sobre o texto do código.

## CI

Dois workflows em `.github/workflows/`:
- **`security-tests.yml`** — sobe MongoDB + backend e roda `security-tests/security-analyzer.py` contra a API viva. Dispara em push/PR (main, dev) e diariamente às 02:00.
- **`mobile-build.yml`** — build local do APK via EAS. Dispara em **todo PR para main/dev sem filtro de `paths`**, então mesmo um PR que só toca o backend espera o build do app.

Ambos enviam email por SMTP e dependem de secrets (`EXPO_TOKEN`, `SMTP_*`).

**Nenhum workflow roda a suíte** ([CI-01](./docs/alinhamento-e-debitos.md#ci-01)) — rode os testes localmente antes do PR, o CI não vai pegar. Outras ferramentas configuradas mas quebradas, todas com ID: typecheck do mobile ([CI-03](./docs/alinhamento-e-debitos.md#ci-03)), lint do frontend ([CI-04](./docs/alinhamento-e-debitos.md#ci-04)) e os 90 erros represados do lint do mobile ([MB-10](./docs/alinhamento-e-debitos.md#mb-10)). Não presuma que um comando de qualidade funciona só porque existe no `package.json`.

## Idioma e convenções de código

- **Domínio em português:** entidades, campos, rotas de pasta e mensagens ao usuário usam PT-BR (`titulo`, `preco`, `Carrinho`). Não traduza campos do MongoDB para inglês.
- Termos técnicos e identificadores de framework ficam na forma original (`store`, `controller`, `blueprint`, `useState`). Comentários e documentação: português.
- Testes: `test_*.py` (backend, exigido pelo `pytest.ini`), `*.test.js`/`*.test.ts` (front/mobile). Ao corrigir um bug, adicione o teste que o reproduz.
- Commits seguem *Conventional Commits*; trabalhe em branch a partir de `main`.

## Regras de domínio

- Cada produto é uma **peça única**: o carrinho não tem quantidade por item — um produto está ou não no carrinho. (Backend e web já seguem; o mobile ainda modela `quantity` — débito `MB-04`.)
- Frete e limite de frete grátis são configuráveis no mobile via `CONFIG.CART`.
