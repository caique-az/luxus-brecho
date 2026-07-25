# Pedidos — `/api/orders`

> Fonte: `backend/app/routes/order_routes.py` · `backend/app/controllers/order_controller.py` · `backend/app/models/order_model.py`
> Contrato geral: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md)

Status possíveis (`ORDER_STATUS`): `pendente`, `confirmado`, `em_preparacao`, `enviado`, `entregue`, `cancelado`. Pedidos criados pela API nascem com `status: "confirmado"`.

## Resumo

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/orders/user/<int:user_id>` | `@owner_or_admin_required("user_id")` | Pedidos do usuário (paginado) |
| GET | `/api/orders/<int:order_id>` | `@jwt_required` + posse no controller | Detalhe de um pedido |
| POST | `/api/orders/user/<int:user_id>` | `@owner_or_admin_required("user_id")` | Cria pedido |
| PUT | `/api/orders/<int:order_id>/status` | `@admin_required` | Atualiza status |
| POST | `/api/orders/<int:order_id>/cancel` | `@jwt_required` + posse no controller | Cancela pedido |

Nas rotas por `order_id`, a posse é verificada **dentro do controller** (`_forbidden_if_not_owner`): carrega o pedido e compara `order.user_id` com `g.user_id`; admin ignora a checagem. Não-dono → 403 `{"message": "Acesso negado. Você não tem permissão para este pedido"}`.

## `GET /api/orders/user/<user_id>`

Query `page` (default 1) / `page_size` (default 20, máx 100 — clamp inline). Ordenado por `created_at` decrescente. Resposta (note a chave `orders`, não `items`):

```json
{
  "orders": [
    {
      "id": 7, "user_id": 5,
      "items": [ { "product_id": 12, "preco": 89.9, "titulo": "...", "imagem": "https://..." } ],
      "total": 89.9, "status": "confirmado",
      "endereco": { "rua": "...", "numero": "...", "bairro": "...", "cidade": "...", "estado": "SP", "cep": "01000000" },
      "created_at": "...", "updated_at": "..."
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total": 3 }
}
```

## `POST /api/orders/user/<user_id>` — criação

Body:

```json
{
  "items": [ { "product_id": 12 }, { "product_id": 15 } ],
  "endereco": { "rua": "...", "numero": "100", "bairro": "...", "cidade": "...", "estado": "SP", "cep": "01000000" }
}
```

Regras (nesta ordem):

1. `endereco` obrigatório com todos os campos (`rua`, `numero`, `bairro`, `cidade`, `estado`, `cep`) e ao menos 1 item — senão 400.
2. Cada `product_id` passa por `coerce_product_id`; **um único não-int rejeita o pedido inteiro** (400 `{"message": "product_id inválido no pedido"}`). Duplicados são deduplicados (peça única).
3. Produto inexistente → 404 `{"message": "Produto <id> não encontrado"}`; indisponível → 400. Nada de pular item silenciosamente — pedido com 0 itens válidos não é criado.
4. `total` = **soma dos `preco`** dos produtos (sem multiplicação por quantidade — não existe `quantity`).

Efeitos colaterais atômicos (transação Mongo quando o cluster suporta; senão, operações sequenciais em fallback): insere o pedido, marca todos os produtos como `vendido` num único `update_many`, e **esvazia o carrinho** do usuário. Sucesso: 201 `{"message": "Pedido criado com sucesso", "order": {...}}`.

## `PUT /api/orders/<order_id>/status` (admin)

Body `{"status": "enviado"}` — precisa ser um dos `ORDER_STATUS`, senão 400. Sucesso: `{"message": "Status atualizado com sucesso", "order_id": 7, "status": "enviado"}`.

## `POST /api/orders/<order_id>/cancel`

Sem body. Regras: pedido já `cancelado` → 400; `enviado`/`entregue` → 400 (não cancela). No sucesso, os produtos do pedido voltam a `disponivel` e o pedido vira `cancelado`: `{"message": "Pedido cancelado com sucesso", "order_id": 7}`.

## Notas de implementação

- Coleção `orders`; id sequencial via `counters` (`get_next_id`). Índices: `order_id_unique` (único em `id`), `user_orders_by_date` (`user_id` + `created_at` desc), `order_status`.
- Respostas passam por `normalize_order` (datas em ISO; sem `_id`).
- O cancelamento restaura produtos com um `update_one` por item (N+1 pequeno e sem transação — diferente da criação).
