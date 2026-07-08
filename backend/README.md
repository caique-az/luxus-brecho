# Luxus Brechó — Backend

API REST Flask + MongoDB com autenticação JWT, Supabase Storage (imagens) e SMTP (emails).

> Documentação completa: [docs/api-reference.md](../docs/api-reference.md) (contrato da API, ~54 endpoints) · [docs/apps/backend.md](../docs/apps/backend.md) (estado interno) · [docs/setup-e-deploy.md](../docs/setup-e-deploy.md) (tabela de env vars). Este README é só o essencial para subir o serviço.

## 🚀 Início Rápido

```bash
pip install -r requirements.txt
cp .env.example .env  # Configure as variáveis
python run.py         # http://localhost:5000/api
```

## ⚙️ Configuração (.env)

Use o `.env.example` como base. Dois pontos críticos:

- **`JWT_SECRET_KEY` é obrigatória** — sem ela o app **não sobe** (fail-fast no import). O algoritmo é HS256 fixo no código (`JWT_ALGORITHM` do env é ignorada).
- **`ADMIN_EMAIL` / `ADMIN_PASSWORD` semeiam o primeiro admin** no boot — sem essas variáveis, **nenhum admin é criado** (não existe credencial padrão).

Sem `MONGODB_URI` o servidor sobe mesmo assim; rotas que dependem do banco respondem `503`. A tabela completa de variáveis (com defaults e onde cada uma é lida) está em [docs/setup-e-deploy.md](../docs/setup-e-deploy.md#variáveis-de-ambiente-do-backend-backendenv).

## 📂 Estrutura

```
app/
├─ routes/       # Blueprints: URL + método + decorators de auth
├─ controllers/  # Lógica de negócio (produtos e health são inline na rota)
├─ models/       # Acesso ao Mongo + ensure_*() de coleções/índices
├─ services/     # JWT, Email, Supabase Storage
├─ utils/        # require_db, serialize_doc, parse_pagination, cache
└─ __init__.py   # App factory (CORS, rate limit, Mongo, blueprints)
```

## 🔐 Autenticação JWT

`Authorization: Bearer <access_token>` — access de 24h, refresh de 30 dias (`POST /api/users/refresh-token`). Decorators disponíveis:

- `@jwt_required` — token válido
- `@jwt_optional` — token opcional
- `@admin_required` — apenas administrador
- `@owner_or_admin_required('<param>')` — dono do recurso ou admin

Todos releem `tipo`/`ativo` do banco a cada request (frescor de privilégio). Detalhes em [docs/api-reference.md](../docs/api-reference.md#autenticação).

## 📌 Endpoints

O inventário completo (8 blueprints, um doc por recurso) está em [docs/api-reference.md](../docs/api-reference.md#índice-de-recursos). Atalhos úteis:

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | Status da API |
| POST | `/api/users/auth` | Login (retorna tokens) |
| POST | `/api/users` | Registro (sempre cria Cliente) |
| GET | `/api/products` | Listar produtos |

## 🧪 Testes

```bash
pytest                # config em pytest.ini (-v --tb=short)
pytest tests/test_products.py::test_nome   # um teste
```

~185 testes contra um mock de Mongo em memória (`tests/conftest.py`) — validators e índices reais não são exercitados.

## 📦 Dependências Principais

- **Flask** + **Flask-CORS** (+ opcionais: flask-compress, flask-limiter)
- **PyMongo** (MongoDB) · **PyJWT** (auth) · **bcrypt** (senhas)
- **supabase** + **Pillow** (imagens) · **python-dotenv** · **pytest**
