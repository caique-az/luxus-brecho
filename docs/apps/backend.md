# Backend — estado interno

> Fonte: `backend/app/` · `backend/tests/` · `backend/run.py` · `backend/index.py`
> Contrato da API: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md#débitos-do-backend)

API Flask + PyMongo. A visão de camadas e o ciclo de boot estão em [arquitetura.md](../arquitetura.md#backend--camadas); aqui fica o detalhe interno para quem vai mexer no código.

## Fluxo de uma requisição

```
rota (routes/X_routes.py)
  → decorators: auth (@jwt_required/@admin_required/@owner_or_admin_required) e @require_db
  → controller (controllers/X_controller.py) — produtos e health são inline na rota
  → model (models/X_model.py): get_collection / validate_* / prepare_new_* / normalize_*
  → resposta: serialize_doc / normalize_* (nunca vaza _id, senha_hash ou tokens)
```

## `app/utils/` — helpers canônicos

| Helper | Arquivo | O que faz |
|--------|---------|-----------|
| `require_db(f)` | `utils/db.py` | Decorator: 503 `{"message": "Banco de dados indisponível"}` se `current_app.db is None`. Substituiu ~46 guards inline com 3 mensagens divergentes. |
| `serialize_doc(doc)` | `utils/serialization.py` | Cópia do dict sem `_id`. Forma canônica que unificou os `_serialize` espalhados (e corrigiu o vazamento de `_id` em favoritos). Não remove campos sensíveis de usuário — para isso, `normalize_user`. |
| `parse_pagination(...)` | `utils/pagination.py` | Lê `page`/`page_size` da query com clamp (`page_size` ≤ 100) e retorna `(page, page_size, skip)`. Por ora aplicado só em `list_users` ([BE-08](../alinhamento-e-debitos.md#be-08)). |
| cache de categorias | `utils/cache.py` | `TTLCache` (cachetools) com `Lock`: `get_cached_categories` (TTL 5 min, usado na validação de produto), `invalidate_categories_cache` (chamado em toda mutação de categoria), `get/set_cached_value` (TTL 10 min), `CacheStats`. |

## `app/services/`

**`jwt_service.py`** — PyJWT, HS256 fixo ([BE-05](../alinhamento-e-debitos.md#be-05)); `JWT_SECRET_KEY` obrigatória (RuntimeError no import). Access 24h / refresh 30d. Convenção única de identidade: `sub` é gravado como str e lido como int (`get_user_id_from_payload`). Os 4 decorators + `_load_fresh_user` (frescor de privilégio: relê `tipo`/`ativo` a cada request; o token nunca eleva privilégio, o banco só revoga). Erros de auth respondem no envelope padrão `{"success": false, "message": ...}`.

**`email_service.py`** — SMTP puro (`smtplib` + MIME), configurado por `SMTP_*`/`FROM_*`. Sem credenciais, loga e retorna `False` (não quebra o fluxo). `get_app_url()` resolve a base dos links por prioridade: `PRODUCTION_URL` → `APP_URL` → `network-config.json` → `http://localhost:5000`. Templates HTML inline para: confirmação de cadastro (24h), boas-vindas, reset de senha (`FRONTEND_URL/redefinir-senha/<token>`, 1h), código de exclusão de conta (6 dígitos, 30 min), notificação de status de pedido. Envio **síncrono** no caminho da requisição ([BE-09](../alinhamento-e-debitos.md#be-09)).

**`supabase_storage.py`** — `SupabaseStorageService` (instância global `storage_service`). Inicialização tolerante (sem `SUPABASE_*` o app sobe; `is_available()`). `upload_image`: valida MIME, redimensiona com Pillow (máx 1200×1200, JPEG q85), nomeia com UUID sob `product_<id>/`, retorna signed URL de 1 ano. Retry de RLS com `SUPABASE_SERVICE_ROLE_*`. Também `delete_image`, `list_product_images`, `get_image_info`.

## Entrypoints

- **`run.py`** — execução local. Lê `network-config.json` da raiz (se existir) para host/porta/IP; senão `FLASK_HOST`/`FLASK_PORT` (default `0.0.0.0:5000`). Usa `use_reloader=False` de propósito (evita `WinError 10038` no Windows).
- **`index.py`** — handler serverless da Vercel (reexporta o app da factory).

## Configuração

**`app/config.py` é a superfície de configuração**: cada env var tem uma função lá, que concentra nome, default e parsing — nenhum módulo lê `os.environ` por conta própria. São funções (não constantes) de propósito: ler no import congelaria o valor antes de os testes ajustarem o ambiente (`test_phase4_admin_seed.py` faz `monkeypatch.setenv("ADMIN_EMAIL", ...)`). Campo numérico inválido avisa e cai no default, em vez de estourar. A exceção deliberada é `JWT_SECRET_KEY`, lida no import de `jwt_service.py` para que a ausência derrube o **startup**, não a primeira requisição autenticada.

A tabela canônica de variáveis (com obrigatoriedade, default e quem consome) está em [setup-e-deploy.md](../setup-e-deploy.md).

## Testes (`backend/tests/`)

13 arquivos, ~185 testes (`pytest`, config em `pytest.ini`: `-v --tb=short`).

| Arquivo | Foco |
|---------|------|
| `test_products/users/categories/cart/orders/favorites/health` | CRUD e caminho feliz de cada blueprint |
| `test_authorization.py` | Anônimo → 401; usuário acessando recurso alheio → 403; operação admin por cliente → 403 |
| `test_jwt_service.py` | Normalização do `sub` para int, refresh, fail-fast do `JWT_SECRET_KEY` |
| `test_phase3_privilege.py` | Registro público sempre Cliente; `/admin` só admin; exclusão endurecida; frescor de privilégio |
| `test_phase4_admin_seed.py` | Seed de admin seguro (sem env → sem admin; senha fraca rejeitada) |
| `test_phase5_domain.py` | Injeção NoSQL no carrinho; pedido "peça única"; `product_id` inválido |
| `test_phase6_structural.py` | `serialize_doc`/`parse_pagination`; não-vazamento de `_id`; escape de regex |

**`conftest.py`** implementa um **mock de Mongo em memória** (`MockCollection`/`MockDatabase` com suporte a `$or/$in/$ne/$gt/$regex/$push/$pull/$inc` e upsert) e define `JWT_SECRET_KEY` antes de importar a app. Fixtures principais: `app`/`client`, `mock_db`, e `auth_headers`/`admin_headers` (id 99)/`user_headers` (id 1) — as factories de header **semeiam o usuário correspondente** no mock, necessário por causa do frescor de privilégio.

**Limitação documentada:** a suíte roda contra o mock — validators JSON Schema, índices únicos e transações **reais** do Mongo não são exercitados ([BE-06](../alinhamento-e-debitos.md#be-06)).

## Código morto conhecido

`health_controller.check_health`, `categories_controller.deactivate_category` (sem rota) e o import de `jwt_optional` em `products_routes.py` — [BE-02](../alinhamento-e-debitos.md#be-02).
