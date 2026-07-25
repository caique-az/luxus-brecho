# Referência da API — contrato geral

> Fonte: `backend/app/__init__.py` · `backend/app/services/jwt_service.py` · `backend/app/utils/`
> Divergências conhecidas: [alinhamento-e-debitos.md](./alinhamento-e-debitos.md)

Este documento cobre o que vale para a API inteira (autenticação, formatos de resposta, paginação, erros, rate limiting). O detalhe de cada recurso — rotas, payloads e shapes de resposta — vive em um arquivo por blueprint em [`docs/api/`](#índice-de-recursos).

## Base

- Base URL local: `http://localhost:5000` (ver [setup-e-deploy.md](./setup-e-deploy.md)). Todas as rotas de negócio ficam sob `/api`.
- Corpo de requisição e resposta: JSON (`Content-Type: application/json`), exceto uploads (multipart/form-data).
- IDs são **inteiros sequenciais** próprios (coleção `counters`), não `ObjectId`.
- `strict_slashes = False` global: `/api/products` e `/api/products/` são equivalentes.
- `GET /` (raiz, fora de `/api`) responde `{message, version, status, database, endpoints}` — útil como ping.

## Autenticação

Autenticação é **sempre via JWT** (`Authorization: Bearer <access_token>`) — usuários, escrita de produtos e categorias (admin), e também carrinho, pedidos e favoritos. JWT assinado com **HS256** — o algoritmo é fixo no código (`jwt_service.py`); a env var `JWT_ALGORITHM` é ignorada ([BE-05](./alinhamento-e-debitos.md#be-05)). `JWT_SECRET_KEY` é obrigatória: o serviço lança `RuntimeError` no import se ela não existir (o app não sobe).

- **Access token**: expira em **24h**; claims `sub` (id do usuário, como string), `type` (`Cliente`/`Administrador`), `email`, `iat`, `exp`, `token_type: "access"`.
- **Refresh token**: expira em **30 dias**; claims `sub`, `iat`, `exp`, `token_type: "refresh"`.
- Envio: header `Authorization: Bearer <access_token>`.
- O `sub` é gravado como string mas **normalizado para int** em toda leitura (`get_user_id_from_payload`) — o banco guarda `id` como int, e a identidade vem sempre do token (`g.user_id`), nunca da URL.

### Decorators de auth

| Decorator | Regra | Em caso de negação |
|-----------|-------|--------------------|
| `@jwt_required` | Exige access token válido; popula `g.user_id`/`g.user_type`/`g.user_email` | 401 `{"success": false, "message": ...}` |
| `@jwt_optional` | Popula `g.*` se houver token válido; senão segue com `g.user_id = None` | nunca nega |
| `@admin_required` | Exige access token com `type: "Administrador"` **e** confirma no banco que ainda é admin ativo | 401/403 `{"success": false, "message": ...}` |
| `@owner_or_admin_required('<param>')` | Exige que `g.user_id` == parâmetro de URL indicado, ou que o usuário seja admin | 401/403 `{"success": false, "message": ...}` |

**Frescor de privilégio:** os decorators releem `tipo`/`ativo` do banco a cada requisição (`_load_fresh_user`). Conta desativada → 403 na próxima requisição; admin rebaixado perde o privilégio imediatamente; usuário excluído → 401. O token nunca **eleva** privilégio (o 1º gate é a claim); o banco só **revoga**. Sem banco acessível, degrada para as claims do token (as rotas de negócio já respondem 503 nesse cenário).

## Formatos de resposta

Todo endpoint responde no **envelope plano** `{ "success": bool, ... }`: `success` é sempre o discriminador e os dados de domínio ficam no topo, ao lado dele (não aninhados sob `data`). O corpo é montado pelos helpers `ok()` / `err()` de `utils/responses.py`.

Sucesso:
```json
{ "success": true, "message": "...", "items": [ ] }
```

Erro — mesma forma, com a mensagem **sempre** em `message` (a chave `error` foi abolida, inclusive nos erros dos decorators JWT) e, em validação, o mapa `errors: { campo: motivo }`:
```json
{ "success": false, "message": "erro de validação", "errors": { "email": "obrigatório" } }
```

**Exceções ao envelope:**
- `GET /api/health` usa a forma **aninhada** `{ "success": true, "data": { ... } }`.
- Endpoints que devolvem uma **lista pura** (ex.: `GET /api/categories/summary`) retornam o array direto.
- `GET /api/products/<id>` e afins retornam o **documento cru** do recurso, sem envelope.

Listagens paginadas trazem `{ "items": [...], "pagination": {...} }` ao lado de `success` (pedidos usam `"orders"`, favoritos usam `"favorites"` + `"total"`).

O `_id` interno do Mongo nunca vaza nas respostas — a serialização canônica é `utils/serialization.serialize_doc` (usuários passam por `normalize_user`, que também remove `senha_hash` e tokens). Exceção deliberada: o carrinho expõe o `_id` do documento de carrinho como string no campo `id`.

Códigos comuns: `200` OK · `201` criado · `400` validação · `401` não autenticado · `403` sem permissão · `404` inexistente · `405` método inválido · `409` conflito · `410` token/código expirado · `413` arquivo grande · `429` rate limit/tentativas esgotadas · `503` banco indisponível.

## Paginação

Query string `page` (≥ 1, default 1) e `page_size` (1–100, default 20; categorias usam default 10). Shape de resposta:

```json
{ "items": [...], "pagination": { "page": 1, "page_size": 20, "total": 42 } }
```

O clamp de `page_size` em 100 evita `.limit()` ilimitado. O helper canônico é `utils/pagination.parse_pagination`, mas por ora só `GET /api/users` o usa — os demais fazem o clamp inline ([BE-08](./alinhamento-e-debitos.md#be-08)).

## Erros globais, rate limiting e banco indisponível

- **Error handlers** (`app/__init__.py`): 404, 405, 413 (payload > 16MB) e 500 respondem `{"success": false, "message": ...}`.
- **Rate limiting** (flask-limiter, se instalado): limite default de **200/dia e 50/hora por IP** em todas as rotas, mais limites específicos nas rotas sensíveis de usuários (login 10/min, exclusão de conta 5/h etc. — ver [api/users-auth.md](./api/users-auth.md)). Storage configurável via `RATELIMIT_STORAGE_URI` (default `memory://`, com warning em produção).
- **Banco indisponível**: o app sobe mesmo sem `MONGODB_URI`. Toda rota que toca o banco é decorada com `@require_db` (`utils/db.py`) e responde **503** `{"success": false, "message": "Banco de dados indisponível"}` quando `app.db is None`.
- **CORS**: origens permitidas vêm de `FRONTEND_ORIGIN` (CSV) ou de uma lista default (Vite, Expo, Vercel). Headers permitidos incluem `Authorization`; `X-User-Id` **não** é mais um header aceito.

## Índice de recursos

| Recurso | Doc | Blueprint (prefixo) | Endpoints |
|---------|-----|---------------------|-----------|
| Usuários e autenticação | [api/users-auth.md](./api/users-auth.md) | `users_bp` (`/api/users`) | 17 |
| Produtos | [api/products.md](./api/products.md) | `products_bp` (`/api/products`) | 8 |
| Categorias | [api/categories.md](./api/categories.md) | `categories_bp` (`/api/categories`) | 7 |
| Carrinho | [api/cart.md](./api/cart.md) | `cart_bp` (`/api/cart`) | 5 |
| Pedidos | [api/orders.md](./api/orders.md) | `order_bp` (`/api/orders`) | 5 |
| Favoritos | [api/favorites.md](./api/favorites.md) | `favorites_bp` (`/api/favorites`) | 5 |
| Imagens | [api/images.md](./api/images.md) | `images_bp` (`/api/images`) | 5 |
| Health | [api/health.md](./api/health.md) | `health_bp` (`/api`) | 2 |

Cada arquivo mapeia 1:1 para o blueprint homônimo em `backend/app/routes/` — ao alterar uma rota, decorator ou shape de resposta, atualize o arquivo correspondente no mesmo PR.
