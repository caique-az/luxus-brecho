# Setup e Deploy

> Fonte: `backend/.env.example` · `backend/run.py` · `sync-network.js` · `start-dev.js` · `*/vercel.json`
> Divergências conhecidas: [alinhamento-e-debitos.md](./alinhamento-e-debitos.md)

Guia para subir o ambiente de desenvolvimento das três aplicações e publicá-las. Esta é a **casa única** da tabela de variáveis de ambiente — os demais docs linkam para cá.

## Pré-requisitos

| Ferramenta | Versão | Para |
|------------|--------|------|
| Python | ≥ 3.10 | Backend |
| Node.js | ≥ 18 | Frontend, Mobile e scripts da raiz |
| MongoDB | local ou Atlas | Banco de dados |
| Expo Go | app no celular | Testar o mobile em dispositivo físico |

Contas externas opcionais (mas necessárias para funcionalidades completas): **Supabase** (imagens) e um provedor **SMTP** (emails, ex.: Gmail com senha de app).

## Subindo tudo rápido (a partir da raiz)

```bash
# 1. Sincroniza o IP da rede (gera network-config.json)
npm run dev

# 2. Sobe backend + mobile juntos (start-dev.js — não inclui o frontend web)
npm run dev:full
```

Ou rode cada parte isoladamente:

```bash
npm run backend    # Flask em :5000
npm run frontend   # Vite em :5173
npm run mobile     # Expo (Metro + QR code)
```

## Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env      # edite as variáveis
python run.py             # http://localhost:5000/api
```

`run.py` lê `network-config.json` da raiz (se existir) para definir host/porta/IP; sem o arquivo, cai para as variáveis `FLASK_HOST`/`FLASK_PORT`. O reloader do Flask fica **desligado de propósito** (`use_reloader=False`) para evitar `WinError 10038` no Windows.

Dois comportamentos de boot que valem destacar:

- **`JWT_SECRET_KEY` é obrigatória (fail-fast):** sem ela o app **não sobe** — `jwt_service.py` lança `RuntimeError` no import. Não existe mais fallback embutido.
- **Seed do primeiro admin:** no primeiro boot com banco, `ADMIN_EMAIL`/`ADMIN_PASSWORD` semeiam o administrador inicial. **Sem essas variáveis, nenhum admin é criado** (não há credencial padrão). A senha precisa passar na política (mín. 6 chars, ≥1 letra e ≥1 número).

### Variáveis de ambiente do backend (`backend/.env`)

Não há `config.py` — cada variável é lida inline no arquivo indicado ([BE-04](./alinhamento-e-debitos.md#be-04)). As marcadas com ⚠️ **não constam do `.env.example`** ([BE-03](./alinhamento-e-debitos.md#be-03)).

| Variável | Obrigatória? | Default | Onde é lida |
|----------|--------------|---------|-------------|
| `JWT_SECRET_KEY` | **sim** (app não sobe) | — | `services/jwt_service.py` |
| `MONGODB_URI` | não (sem ela, rotas de banco respondem 503) | — | `app/__init__.py` |
| `MONGODB_DATABASE` | não | database da URI | `app/__init__.py` |
| `MONGO_SERVER_SELECTION_MS` ⚠️ | não | `15000` | `app/__init__.py` |
| `MONGO_CONNECT_TIMEOUT_MS` ⚠️ / `MONGO_SOCKET_TIMEOUT_MS` ⚠️ | não | `20000` | `app/__init__.py` |
| `MONGO_MAX_POOL_SIZE` ⚠️ | não | `50` | `app/__init__.py` |
| `MONGO_APPNAME` ⚠️ | não | `Luxus-Brecho-Backend` | `app/__init__.py` |
| `SECRET_KEY` ⚠️ | não | `dev-secret-key` | `app/__init__.py` |
| `MAX_CONTENT_LENGTH` ⚠️ | não | `16777216` (16MB) | `app/__init__.py` |
| `FLASK_DEBUG` | não | `False` | `app/__init__.py`, health |
| `FLASK_ENV` ⚠️ | não | `production` | `routes/health_routes.py` |
| `FLASK_HOST` ⚠️ / `FLASK_PORT` ⚠️ | não | `0.0.0.0` / `5000` | `run.py` (se não houver `network-config.json`) |
| `FRONTEND_ORIGIN` | não | lista embutida (localhost + Vercel) | `app/__init__.py` (CORS, CSV) |
| `RATELIMIT_STORAGE_URI` | não | `memory://` (warning em produção) | `app/__init__.py` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | para o seed do 1º admin | — (sem elas, sem seed) | `models/user_model.py` |
| `ADMIN_NAME` | não | `Administrador` | `models/user_model.py` |
| `SUPABASE_URL` / `SUPABASE_KEY` | para upload de imagens | — (serviço fica indisponível) | `services/supabase_storage.py` |
| `SUPABASE_BUCKET` | não | `product-images` | `services/supabase_storage.py` |
| `SUPABASE_SERVICE_ROLE_EMAIL` ⚠️ / `SUPABASE_SERVICE_ROLE_KEY` ⚠️ | não (retry de RLS) | — | `services/supabase_storage.py` |
| `SMTP_HOST` / `SMTP_PORT` | não | `smtp.gmail.com` / `587` | `services/email_service.py` |
| `SMTP_USER` / `SMTP_PASSWORD` | para envio de e-mails | — (sem elas, e-mails só logam) | `services/email_service.py` |
| `FROM_EMAIL` / `FROM_NAME` | não | `SMTP_USER` / `Luxus Brechó` | `services/email_service.py` |
| `FRONTEND_URL` | para links de reset de senha | `http://localhost:5173` | `services/email_service.py` |
| `PRODUCTION_URL` ⚠️ / `APP_URL` ⚠️ | não (base dos links de e-mail em produção) | fallback: `network-config.json` → localhost | `services/email_service.py` |

Notas:
- Sem `MONGODB_URI` o servidor **ainda sobe**, mas rotas que dependem do banco respondem `503` (decorator `@require_db`).
- As libs `flask-compress` e `flask-limiter` são opcionais: se instaladas, ativam gzip e rate limiting automaticamente. Em produção/serverless, aponte `RATELIMIT_STORAGE_URI` para um storage compartilhado (ex.: `redis://...`).

## Frontend

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173
```

Variável de ambiente (`frontend/.env`):
```ini
VITE_API_URL=http://127.0.0.1:5000
```
O cliente anexa `/api` a essa base. Sem a variável, o fallback é `http://127.0.0.1:5000`.

## Mobile

```bash
cd mobile
npm install
cp .env.example .env
npx expo start --clear    # abre Metro + QR code
```

Escaneie o QR code com o **Expo Go**. Para dispositivo físico, o celular e o PC precisam estar na **mesma rede Wi-Fi**.

Variáveis (`mobile/.env`, prefixo obrigatório `EXPO_PUBLIC_`):
```ini
EXPO_PUBLIC_API_URL=http://SEU_IP:5000/api
EXPO_PUBLIC_PRODUCTION_URL=https://sua-api-producao/api
EXPO_PUBLIC_ENABLE_LOGS=true
```
Toda configuração do app vive em `constants/config.ts` e pode ser sobrescrita por variáveis `EXPO_PUBLIC_*` (timeouts, retries, cache, frete, paginação).

## Configuração de rede para o mobile (passo crítico)

O mobile precisa alcançar o backend pelo **IP da máquina na Wi-Fi**, não por `localhost`. O fluxo automatiza isso:

1. Na **raiz**, rode `npm run dev`. O `sync-network.js` detecta o IPv4 da rede (`ipconfig` no Windows, `ifconfig`/`ip addr` no Linux/macOS) e escreve:
   - `network-config.json` na raiz (lido pelo backend);
   - `mobile/network-config.json` (lido pelo app em dev via `require`).
2. Reinicie o backend para ele pegar o novo IP.
3. Inicie o mobile com `npx expo start --clear` (o `--clear` evita cache de URL antiga).

Checklist quando o app não conecta:
- O backend está rodando em `0.0.0.0:5000` (e não só `127.0.0.1`)?
- Celular e PC na mesma rede Wi-Fi?
- Firewall liberando a porta 5000?
- O IP em `network-config.json` corresponde ao IP atual? (Rode `npm run dev` de novo após trocar de rede.)
- Teste direto: `curl http://<IP>:5000/api/health`.

> `network-config.json` é **gerado** e não versionado. Use `network-config.example.json` como referência.

## Testes

```bash
cd backend && pytest          # backend (config em pytest.ini)
cd frontend && npm test       # Vitest (watch)
```

O mobile tem `jest.config.js`, mas **nenhuma suíte** — `npm test` não exercita nada ([MB-07](./alinhamento-e-debitos.md#mb-07)).

Rodar um teste isolado:
```bash
pytest tests/test_products.py::test_nome      # backend
npx vitest run src/store/cartStore.test.js    # frontend
```

## Deploy

### Backend → Vercel (serverless Python)

`backend/vercel.json` usa `@vercel/python` sobre `index.py`, que reexporta o app Flask. Todas as rotas caem no mesmo handler.

- Configure as variáveis de ambiente (tabela acima) no painel da Vercel — em especial `JWT_SECRET_KEY` (sem ela o deploy não sobe) e `RATELIMIT_STORAGE_URI` (Redis).
- Garanta que o IP de saída esteja liberado no **MongoDB Atlas** (ou libere `0.0.0.0/0` com cautela).
- Ajuste `FRONTEND_ORIGIN` para o domínio de produção do frontend.

### Frontend → Vercel (SPA estática)

`frontend/vercel.json` faz rewrite de `/(.*)` para `/index.html`, necessário para o roteamento client-side do React Router.

- Build command: `npm run build` · Output: `dist/`.
- Defina `VITE_API_URL` apontando para o backend em produção.

### Mobile → Expo / EAS

Distribuído fora da Vercel, via `eas.json`. Configure `EXPO_PUBLIC_PRODUCTION_URL` para a API de produção — em build de produção, `getApiUrl()` usa essa URL.

## Segurança

Há um script de verificação rápida em `security-tests/security-analyzer.py` que checa, contra um backend rodando localmente, itens como headers de segurança e respostas da API. Útil como smoke test antes de publicar.
