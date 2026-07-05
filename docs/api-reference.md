# Referência da API

API REST do Luxus Brechó. Todas as rotas têm prefixo **`/api`** e respondem JSON.

- **Base URL (local):** `http://localhost:5000/api`
- **Base URL (rede/mobile):** `http://<IP_DA_MAQUINA>:5000/api`
- **IDs** são inteiros sequenciais próprios (não `ObjectId`).
- `strict_slashes` está **desligado**: barra final é indiferente.

## Autenticação

Autenticação é **sempre via JWT** (`Authorization: Bearer <access_token>`): usuários, escrita de produtos e categorias (admin), e também carrinho, pedidos e favoritos. A identidade vem do token (`g.user_id`).

Tokens são obtidos em `POST /api/users/auth`. O **access token** vale 24h; renove com o **refresh token** (30 dias) em `POST /api/users/refresh-token`.

Marcação usada abaixo:
- 🔓 público · 🔑 requer JWT · 👑 requer JWT de admin · 👤 dono ou admin

## Convenções de resposta

A maioria dos endpoints retorna um envelope:

```json
{ "success": true, "message": "...", "data": { } }
```

Alguns endpoints de listagem (produtos) retornam diretamente `items` + `pagination`. Erros seguem:

```json
{ "success": false, "message": "erro de validação", "errors": { "campo": "motivo" } }
```

Códigos comuns: `200` OK · `201` criado · `400` validação · `401` não autenticado · `403` sem permissão · `404` inexistente · `405` método inválido · `409` conflito (ID duplicado) · `413` arquivo grande · `503` banco indisponível.

---

## Health

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/health` | 🔓 | Status da API, uso de memória, ambiente e versão |

---

## Usuários (`/api/users`)

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/users` | 👑 | Lista usuários |
| GET | `/api/users/<id>` | 👤 | Detalhe de um usuário |
| POST | `/api/users` | 🔓 | Registro de usuário |
| PUT | `/api/users/<id>` | 👤 | Atualiza dados |
| DELETE | `/api/users/<id>` | 👑 | Exclui usuário |
| POST | `/api/users/auth` | 🔓 | Login → retorna tokens *(rate limit: 10/min, 50/h)* |
| POST | `/api/users/refresh-token` | 🔓 | Renova o access token |
| PUT | `/api/users/<id>/change-password` | 👤 | Altera senha |
| POST | `/api/users/forgot-password` | 🔓 | Inicia recuperação de senha *(5/h)* |
| POST | `/api/users/reset-password` | 🔓 | Define nova senha via token *(10/h)* |
| GET | `/api/users/confirm-email/<token>` | 🔓 | Confirma email de cadastro |
| POST | `/api/users/resend-confirmation` | 🔓 | Reenvia email de confirmação *(3/h)* |
| GET | `/api/users/types` | 🔓 | Tipos de usuário (`Administrador`, `Cliente`) |
| GET | `/api/users/summary` | 🔓 | Resumo/estatísticas de usuários |
| POST | `/api/users/request-deletion` | 🔓 | Solicita exclusão de conta (envia código) |
| POST | `/api/users/confirm-deletion` | 🔓 | Confirma exclusão de conta com código |

**Registro — `POST /api/users`**
```json
{ "nome": "Maria", "email": "maria@ex.com", "senha": "Senha@123", "tipo": "Cliente" }
```
Regras: `nome` 2–100 chars; `email` válido e único; `tipo` ∈ {`Administrador`, `Cliente`}. Clientes nascem **inativos** até confirmar o email; administradores já nascem ativos e confirmados.

**Login — `POST /api/users/auth`**
```json
{ "email": "maria@ex.com", "senha": "Senha@123" }
```
Retorna o usuário + `access_token` e `refresh_token`. Se o email não foi confirmado, a resposta sinaliza essa condição.

---

## Produtos (`/api/products`)

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/products` | 🔓 | Lista com filtro e paginação |
| GET | `/api/products/<id>` | 🔓 | Detalhe do produto |
| GET | `/api/products/category/<categoria>` | 🔓 | Produtos de uma categoria |
| POST | `/api/products` | 👑 | Cria produto (JSON) |
| POST | `/api/products/with-image` | 👑 | Cria produto enviando imagem (multipart) |
| PUT | `/api/products/<id>` | 👑 | Atualiza produto (merge parcial) |
| PUT | `/api/products/<id>/image` | 👑 | Substitui apenas a imagem |
| DELETE | `/api/products/<id>` | 👑 | Exclui produto (e remove imagem do storage) |

**Listagem — `GET /api/products`** · query params:

| Param | Default | Limite | Descrição |
|-------|---------|--------|-----------|
| `page` | 1 | 1–1000 | Página |
| `page_size` | 20 | 1–100 | Itens por página |
| `categoria` | — | ≤50 chars | Filtra por categoria |
| `q` | — | ≤100 chars | Busca textual (índice de texto) |

Resposta:
```json
{
  "items": [ { "id": 1, "titulo": "...", "preco": 99.9, "categoria": "Casual", "imagem": "https://...", "status": "disponivel" } ],
  "pagination": { "page": 1, "page_size": 20, "total": 42 }
}
```

**Criação — `POST /api/products`** (admin):
```json
{ "titulo": "Camisa Linho", "preco": 89.9, "descricao": "...", "categoria": "Casual", "imagem": "https://..." }
```
Regras: `titulo` 2–100 chars; `preco` numérico ≥ 0; `categoria` precisa ser uma **categoria ativa**; `status` opcional ∈ {`disponivel`, `indisponivel`, `vendido`} (default `disponivel`). O `id` é gerado automaticamente.

**Criação com imagem — `POST /api/products/with-image`** (multipart/form-data): campos `titulo`, `descricao`, `preco`, `categoria` + arquivo `image`. Formatos aceitos: `png, jpg, jpeg, gif, webp`; tamanho máximo **5MB**. O backend sobe a imagem ao Supabase e grava a URL no produto.

---

## Categorias (`/api/categories`)

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/categories` | 🔓 | Lista categorias |
| GET | `/api/categories/<id>` | 🔓 | Detalhe |
| GET | `/api/categories/summary` | 🔓 | Resumo (ex.: contagem por categoria) |
| POST | `/api/categories` | 👑 | Cria categoria |
| PUT | `/api/categories/<id>` | 👑 | Atualiza categoria |
| PUT | `/api/categories/<id>/activate` | 👑 | Ativa categoria |
| DELETE | `/api/categories/<id>` | 👑 | Remove categoria |

Campos: `id` (auto), `name`, `description`, `active`. As **categorias ativas** definem dinamicamente quais valores de `categoria` os produtos podem usar.

> As rotas de escrita de categoria exigem **JWT de administrador** (`@admin_required`), mesmo critério do CRUD de produtos. A leitura permanece pública.

---

## Imagens (`/api/images`)

Integração com Supabase Storage.

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/images/upload` | Upload de imagem única |
| POST | `/api/images/upload-multiple` | Upload de múltiplas imagens |
| DELETE | `/api/images/delete` | Remove imagem |
| GET | `/api/images/product/<product_id>` | Lista imagens de um produto |
| POST | `/api/images/info` | Metadados de uma imagem |

---

## Favoritos (`/api/favorites`) 🔑

Todas as rotas exigem **JWT** (`Authorization: Bearer`). A identidade vem do token; não há mais `X-User-Id`.

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/favorites` | 🔑 | Lista favoritos do usuário |
| POST | `/api/favorites` | 🔑 | Adiciona produto (`{ "product_id": 12 }`) |
| DELETE | `/api/favorites/<product_id>` | 🔑 | Remove dos favoritos |
| GET | `/api/favorites/check/<product_id>` | 🔑 | Indica se está favoritado |
| POST | `/api/favorites/toggle` | 🔑 | Alterna favorito (`{ "product_id": 12 }`) |

---

## Carrinho (`/api/cart`)

Exige **JWT**: o `user_id` da URL deve ser o dono do token (ou admin). Lembre: produto é **peça única** — não há quantidade real por item.

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/cart/<user_id>` | 👤 | Carrinho do usuário |
| POST | `/api/cart/<user_id>/add` | 👤 | Adiciona item |
| POST | `/api/cart/<user_id>/remove` | 👤 | Remove item |
| PUT | `/api/cart/<user_id>/update` | 👤 | Atualiza item |
| DELETE | `/api/cart/<user_id>/clear` | 👤 | Esvazia o carrinho |
| POST | `/api/cart/<user_id>/sync` | 👤 | Sincroniza carrinho local ↔ servidor |

---

## Pedidos (`/api/orders`)

Exige **JWT**. Listar/criar por usuário: dono da URL ou admin (👤). Ver/cancelar um pedido: dono do pedido ou admin. Atualizar status: **admin** (👑).

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/orders/user/<user_id>` | 👤 | Lista pedidos do usuário |
| GET | `/api/orders/<order_id>` | 👤 | Detalhe do pedido (dono ou admin) |
| POST | `/api/orders/user/<user_id>` | 👤 | Cria pedido |
| PUT | `/api/orders/<order_id>/status` | 👑 | Atualiza status |
| POST | `/api/orders/<order_id>/cancel` | 👤 | Cancela pedido (dono ou admin) |

**Criação — `POST /api/orders/user/<user_id>`**
```json
{
  "items": [ { "id": 12, "titulo": "Camisa Linho", "preco": 89.9 } ],
  "total": 104.9,
  "endereco": { "rua": "...", "numero": "100", "bairro": "...", "cidade": "...", "estado": "SP", "cep": "00000-000" }
}
```
Regras: ao menos **1 item**; `endereco` obrigatório com todos os campos (`rua`, `numero`, `bairro`, `cidade`, `estado`, `cep`). O pedido nasce com `status: "pendente"`. Mudanças de status disparam notificação por email.
