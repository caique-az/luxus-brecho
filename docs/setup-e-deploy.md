# Setup e Deploy

Guia para subir o ambiente de desenvolvimento das três aplicações e publicá-las.

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

# 2. Sobe backend + frontend juntos
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

### Variáveis de ambiente (`backend/.env`)

```ini
# Database
MONGODB_URI=mongodb+srv://<USER>:<PASS>@<CLUSTER>/?retryWrites=true&w=majority
MONGODB_DATABASE=luxus_brecho_db

# Flask
FLASK_DEBUG=True
FRONTEND_ORIGIN=http://localhost:5173      # CSV de origens CORS permitidas

# JWT (troque em produção!)
JWT_SECRET_KEY=sua-chave-secreta-32-chars-minimo
JWT_ALGORITHM=HS256

# Supabase Storage (imagens)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-anon-key
SUPABASE_BUCKET=product-images

# Email SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-de-app
FROM_EMAIL=seu-email@gmail.com
FROM_NAME=Luxus Brechó

# URLs
FRONTEND_URL=http://localhost:5173
```

Notas:
- Sem `MONGODB_URI` o servidor **ainda sobe**, mas endpoints que dependem do banco respondem `503`.
- `FRONTEND_ORIGIN` aceita várias origens separadas por vírgula. Sem ela, há um fallback embutido (localhost + domínios Vercel).
- As libs `flask-compress` e `flask-limiter` são opcionais: se instaladas, ativam gzip e rate limiting automaticamente.

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
cd mobile && npm test         # Jest
```

Rodar um teste isolado:
```bash
pytest tests/test_products.py::test_nome      # backend
npx vitest run src/store/cartStore.test.js    # frontend
```

## Deploy

### Backend → Vercel (serverless Python)

`backend/vercel.json` usa `@vercel/python` sobre `index.py`, que reexporta o app Flask. Todas as rotas caem no mesmo handler.

- Configure as variáveis de ambiente (todas do `.env`) no painel da Vercel.
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
