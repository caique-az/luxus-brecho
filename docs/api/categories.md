# Categorias — `/api/categories`

> Fonte: `backend/app/routes/categories_routes.py` · `backend/app/controllers/categories_controller.py` · `backend/app/models/category_model.py`
> Contrato geral: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md)

As **categorias ativas** definem dinamicamente quais valores de `categoria` os produtos podem usar (validação em app + validator do Mongo). Campos: `id` (sequencial), `name`, `description`, `active`.

## Resumo

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/categories/` | pública | Lista com paginação (`active_only` opcional) |
| GET | `/api/categories/<int:id>` | pública | Detalhe |
| GET | `/api/categories/summary` | pública | Lista enxuta das categorias ativas |
| POST | `/api/categories/` | `admin_required` | Cria categoria |
| PUT | `/api/categories/<int:id>` | `admin_required` | Atualiza (merge parcial) |
| DELETE | `/api/categories/<int:id>` | `admin_required` | **Hard delete** (bloqueado se há produtos) |
| PUT | `/api/categories/<int:id>/activate` | `admin_required` | Reativa categoria |

As rotas são registradas no estilo funcional (`categories_bp.route(...)(admin_required(fn))`), mas a regra é a mesma dos decorators: escrita só para admin, leitura pública.

## Leitura

- **`GET /api/categories/`** — query `active_only` (`true`/`false`, default `false`), `page` (default 1), `page_size` (default **10**, máx 100). Ordenada por `name`. Resposta `{"items": [...], "pagination": {...}}`.
- **`GET /api/categories/<id>`** — o documento direto; 404 `{"message": "category not found"}`.
- **`GET /api/categories/summary`** — **array direto** (sem envelope) das categorias ativas: `[{"id": 1, "name": "Casual", "description": "..."}]`.

## Escrita (admin)

**`POST /api/categories/`** — body `{"name", "description", "active"?}`. Aceita `nome` como alias de `name` (normalização). Regras: `name` 2–50 chars e **único** (409 `{"message": "category name already exists"}`); `description` 5–200 chars; `active` default `true`. Sucesso: 201 com o documento direto.

**`PUT /api/categories/<id>`** — merge parcial + revalidação; não permite trocar o `id`; renomeação verifica unicidade do nome. Resposta: o documento atualizado direto.

**`DELETE /api/categories/<id>`** — exclusão **permanente**, recusada se houver produtos na categoria:

```json
{ "message": "não é possível deletar categoria com produtos associados", "products_count": 3 }
```

**`PUT /api/categories/<id>/activate`** — marca `active: true` e responde o documento atualizado.

## Notas de implementação

- Toda mutação invalida o **cache de categorias ativas** (`utils/cache.py`, TTL 5 min), usado na validação de produtos.
- `ensure_categories_collection` aplica o validator e **dropa e recria todos os índices** (exceto `_id_`) a cada boot ([BE-07](../alinhamento-e-debitos.md#be-07)). Índices: `uniq_id` (único), `uniq_name` (único parcial, `name` existente), `idx_active`.
- Existe `deactivate_category` no controller, mas **sem rota registrada** — código morto ([BE-02](../alinhamento-e-debitos.md#be-02)); o soft-disable hoje só é possível via `PUT /<id>` com `{"active": false}`.
- As mensagens deste recurso misturam inglês e português (`"category not found"` vs `"categoria não encontrada"`); documentado como está.
