# Produtos — `/api/products`

> Fonte: `backend/app/routes/products_routes.py` · `backend/app/models/product_model.py`
> Contrato geral: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md)

Produtos são **peças únicas** (regra de domínio): não existe estoque/quantidade — o `status` (`disponivel`/`indisponivel`/`vendido`) diz se a peça pode ser comprada.

Particularidade estrutural: este é o único recurso cuja lógica vive **inline nas rotas** — não há `products_controller.py` (a duplicata antiga era código morto e foi removida).

## Resumo

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/products/` | pública (`@require_db`) | Lista com filtro, busca textual e paginação |
| GET | `/api/products/<int:id>` | pública | Detalhe do produto |
| POST | `/api/products/` | `@admin_required` | Cria produto (JSON) |
| PUT | `/api/products/<int:id>` | `@admin_required` | Atualiza (merge parcial) |
| DELETE | `/api/products/<int:id>` | `@admin_required` | Exclui (e apaga a imagem no Supabase) |
| POST | `/api/products/with-image` | `@admin_required` | Cria produto + upload de imagem (multipart) |
| PUT | `/api/products/<int:id>/image` | `@admin_required` | Substitui só a imagem (multipart) |
| GET | `/api/products/category/<string:categoria>` | pública | Produtos de uma categoria |

## Listagem — `GET /api/products/`

Query string validada por marshmallow (`ProductQuerySchema`):

| Param | Default | Limite | Descrição |
|-------|---------|--------|-----------|
| `page` | 1 | 1–1000 | Página |
| `page_size` | 20 | 1–100 | Itens por página |
| `categoria` | — | ≤ 50 chars | Filtro exato por categoria |
| `q` | — | ≤ 100 chars | Busca `$text` no índice `titulo`+`descricao`, ordenada por relevância |

Parâmetro inválido → 400 `{"success": false, "message": "Parâmetros inválidos", "errors": {...}}` (este é um dos raros pontos que respondem `success` — [BE-01](../alinhamento-e-debitos.md#be-01)). Sem `q`, a ordenação é por `titulo` ascendente. Resposta:

```json
{
  "items": [ { "id": 1, "titulo": "...", "preco": 89.9, "descricao": "...", "categoria": "Casual", "imagem": "https://...", "status": "disponivel" } ],
  "pagination": { "page": 1, "page_size": 20, "total": 42 }
}
```

## Detalhe e listagem por categoria

- **`GET /api/products/<id>`** — o documento direto (via `serialize_doc`); 404 `{"message": "produto não encontrado"}`.
- **`GET /api/products/category/<categoria>`** — mesma paginação (clamp inline), resposta `{"items", "categoria", "pagination"}`; **404** `{"message": "nenhum produto encontrado para essa categoria"}` quando a página vem vazia.

## Criação e atualização

**`POST /api/products/`** — body:

```json
{ "titulo": "Camisa Linho", "preco": 89.9, "descricao": "Camisa de linho...", "categoria": "Casual", "imagem": "https://..." }
```

- Regras (`validate_product`): `titulo` 2–100 chars; `descricao` 10–500 chars; `preco` numérico ≥ 0 (int vira float); `imagem` obrigatória (URL http/https ou caminho `/`); `categoria` precisa ser uma **categoria ativa** (a lista vem do banco com cache de 5 min — `utils/cache.py`); `status` opcional, default `disponivel`.
- `id` é gerado por sequência (`counters`). Erro de validação → 400 `{"message": "erro de validação", "errors": {...}}`; id duplicado → 409.
- Sucesso: **201 com o documento do produto direto** (sem envelope).

**`PUT /api/products/<id>`** — merge parcial sobre o documento atual, revalida tudo, não permite trocar o `id`. Resposta: o documento atualizado direto.

## Fluxos com imagem (multipart/form-data)

**`POST /api/products/with-image`** — campos de formulário `titulo`, `descricao`, `preco`, `categoria` + arquivo `image`.

- Validações de arquivo: extensões `png, jpg, jpeg, gif, webp`; máximo **5MB** (400 com `errors.image` em caso de violação).
- Fluxo atual: sobe a imagem com um id temporário (timestamp), valida o produto, e **sobe de novo** com o id sequencial real, apagando a temporária ([BE-09](../alinhamento-e-debitos.md#be-09) — upload duplo). Se a validação do produto falha, a imagem temporária é removida.
- Sucesso 201: `{"message": "Produto criado com sucesso", "product": {...}}`.

**`PUT /api/products/<id>/image`** — arquivo `image`. Sobe a nova, apaga a antiga, atualiza a URL. Sucesso 200: `{"message": "Imagem atualizada com sucesso", "product": {...}}`.

**`DELETE /api/products/<id>`** — antes de apagar o documento, tenta remover a imagem do Supabase (falha de storage só gera warning). 200 `{"message": "produto excluído"}`.

## Notas de implementação

- Coleção `products` com **JSON Schema validator dinâmico** (`create_dynamic_schema`): o enum de `categoria` é montado a partir das categorias ativas no momento do boot; `validationLevel: "moderate"`. Required: `id`, `titulo`, `preco`, `descricao`, `categoria`, `imagem`.
- Índices: `uniq_id` (único em `id`), `idx_categoria`, `txt_titulo_descricao` (índice TEXT composto).
- `products_routes.py` importa `jwt_optional` sem usá-lo — código morto ([BE-02](../alinhamento-e-debitos.md#be-02)).
