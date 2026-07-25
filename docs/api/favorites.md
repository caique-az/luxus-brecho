# Favoritos — `/api/favorites`

> Fonte: `backend/app/routes/favorites_routes.py` · `backend/app/controllers/favorites_controller.py` · `backend/app/models/favorite_model.py`
> Contrato geral: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md)

Todas as rotas exigem **`@jwt_required`**; a identidade vem de `g.user_id` (o id do token). O esquema antigo por header `X-User-Id` **foi removido** — o header nem consta mais no CORS. Web e mobile já enviam o Bearer, mas ainda anexam o `X-User-Id` legado — ignorado pelo backend ([FE-01](../alinhamento-e-debitos.md#fe-01), [MB-02](../alinhamento-e-debitos.md#mb-02)).

## Resumo

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/favorites/` | Lista favoritos do usuário autenticado, com o produto embutido |
| POST | `/api/favorites/` | Adiciona produto aos favoritos |
| DELETE | `/api/favorites/<int:product_id>` | Remove dos favoritos |
| GET | `/api/favorites/check/<int:product_id>` | Verifica se está favoritado |
| POST | `/api/favorites/toggle` | Alterna favorito |

## `GET /api/favorites/`

Ordenado por `created_at` decrescente; resolve os produtos numa query `$in`:

```json
{
  "favorites": [
    {
      "user_id": 5, "product_id": 12, "created_at": "...",
      "product": { "id": 12, "titulo": "...", "preco": 89.9, ... }
    }
  ],
  "total": 1
}
```

Se o produto favoritado não existe mais, o favorito é mantido com `"product": null`.

## `POST /api/favorites/`

Body `{"product_id": 12}` — `product_id` precisa ser **int** (400 caso contrário). Produto inexistente → 404. Já favoritado → 409 `{"message": "Produto já está nos favoritos"}`. Sucesso: 201

```json
{ "message": "Produto adicionado aos favoritos", "favorite": { "user_id": 5, "product_id": 12, "created_at": "..." } }
```

## `DELETE /api/favorites/<product_id>`

Favorito inexistente → 404. Sucesso: 200 `{"message": "Produto removido dos favoritos"}`.

## `GET /api/favorites/check/<product_id>`

Sempre 200: `{"is_favorited": true}` / `{"is_favorited": false}`.

## `POST /api/favorites/toggle`

Body `{"product_id": 12}` (mesmas validações do add). Se estava favoritado, remove — 200 `{"message": "Produto removido dos favoritos", "is_favorited": false}`. Se não estava, adiciona — 201 `{"message": "Produto adicionado aos favoritos", "is_favorited": true, "favorite": {...}}`.

## Notas de implementação

- Coleção `favorites`. Índices: `user_product_unique` (**único composto** `user_id` + `product_id` — impede favorito duplicado no nível do banco), `user_created` (`user_id` + `created_at`), `product_idx`.
- A serialização usa `utils/serialization.serialize_doc` — a versão antiga deste controller **vazava o `_id`** do Mongo; a centralização corrigiu isso.
