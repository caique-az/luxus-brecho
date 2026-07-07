# Carrinho — `/api/cart`

> Fonte: `backend/app/routes/cart_routes.py` · `backend/app/controllers/cart_controller.py` · `backend/app/models/cart_model.py`
> Contrato geral: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md)

Modelo de **peça única**: um item de carrinho não tem `quantity` — o produto está ou não no carrinho. Cada usuário tem no máximo **um** carrinho (índice único em `user_id`).

> A antiga rota `PUT /api/cart/<user_id>/update` (atualizar quantidade) **não existe mais** — foi removida junto com o campo `quantity`. O mobile ainda modela `quantity` ([MB-04](../alinhamento-e-debitos.md#mb-04)).

## Resumo

Todas as rotas exigem `@owner_or_admin_required("user_id")`: só o dono do carrinho (ou um admin) lê/altera.

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/cart/<int:user_id>` | Carrinho com detalhes dos produtos |
| POST | `/api/cart/<int:user_id>/add` | Adiciona produto (idempotente) |
| POST | `/api/cart/<int:user_id>/remove` | Remove produto |
| DELETE | `/api/cart/<int:user_id>/clear` | Esvazia o carrinho |
| POST | `/api/cart/<int:user_id>/sync` | Substitui o carrinho pelo estado local do cliente |

## `GET /api/cart/<user_id>`

Se o usuário nunca criou carrinho, responde um carrinho vazio (`{"user_id", "items": [], "created_at": null, "updated_at": null}`). Caso contrário, resolve os produtos numa única query `$in` e responde:

```json
{
  "id": "<_id do carrinho como string>",
  "user_id": 5,
  "items": [
    {
      "product_id": 12,
      "added_at": "2026-07-01T12:00:00",
      "product": { "id": 12, "titulo": "...", "preco": 89.9, "imagem": "https://...", "status": "disponivel", "categoria": "Casual" }
    }
  ],
  "created_at": "...", "updated_at": "..."
}
```

Itens cujo produto não existe mais são omitidos da resposta.

## `POST /api/cart/<user_id>/add`

Body `{"product_id": 12}`. O `product_id` passa por `coerce_product_id` — só int (ou string numérica) é aceito; um operador NoSQL como `{"$gt": 0}` → 400 `{"message": "product_id deve ser um inteiro válido"}`.

- Produto inexistente → 404; produto com `status != "disponivel"` → 400.
- **Idempotente**: se o produto já está no carrinho, responde 200 `{"message": "Produto já está no carrinho", "product_id": 12}` sem duplicar.
- Sucesso: 201 `{"message": "Produto adicionado ao carrinho", "product_id": 12}`.

## `POST /api/cart/<user_id>/remove`

Body `{"product_id": 12}`. Faz `$pull` do item; se nada foi removido → 404 `{"message": "Produto não encontrado no carrinho"}`. Sucesso: `{"message": "Produto removido do carrinho", "product_id": 12}`.

## `DELETE /api/cart/<user_id>/clear`

Zera `items`. Sempre 200 `{"message": "Carrinho limpo com sucesso"}` (mesmo se o carrinho não existia).

## `POST /api/cart/<user_id>/sync`

Body `{"items": [{"product_id": 12}, ...]}`. **Substitui** o carrinho do servidor pelo estado enviado:

- `product_id` inválidos (não-int) são **descartados silenciosamente**; duplicados são deduplicados (peça única); só produtos com `status: "disponivel"` sobrevivem.
- Upsert: cria o carrinho se não existir.
- Resposta: `{"message": "Carrinho sincronizado", "items_count": 3}`.

## Notas de implementação

- Coleção `carts`; índice único `user_id_unique`.
- `coerce_product_id` (em `cart_model.py`) é a barreira anti-injeção NoSQL do domínio: rejeita dicts-operadores e `bool`.
- O controller importa `normalize_cart` mas monta a resposta do GET manualmente — pequena duplicação ([BE-02](../alinhamento-e-debitos.md#be-02) documenta os casos de código morto do backend).
