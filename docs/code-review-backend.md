# Code Review — Backend (`backend/`)

> **Data:** 2026-07-01
> **Escopo:** API Flask + MongoDB em `backend/` (routes, controllers, models, services, `__init__.py`).
> **Metodologia:** revisão de _recall_ a esforço extra-alto — 10 ângulos de busca em paralelo (5 de correção + reuso + simplificação + eficiência + altitude + convenções), seguidos de verificação lendo o código diretamente.
> **Status:** este documento é o ponto de partida para **implementar** as correções. Marque os checkboxes conforme cada item for resolvido.

## Resumo executivo

O backend tem um **modelo de autenticação sistemicamente quebrado**: a maioria dos endpoints que deveriam ser protegidos não são (carrinho, pedidos, categorias, imagens), o mecanismo de favoritos usa um header falsificável, e o decorator de posse (`owner_or_admin_required`) tem um bug de tipo que bloqueia até os donos legítimos. Além disso, há um caminho de **auto-registro como administrador**.

Prioridades:

- **P0 (crítico, explorável hoje por anônimo):** itens 1–10 e 15. Corrigir antes de qualquer deploy público.
- **P1 (correção / regra de domínio):** itens 11–14.
- **P2 (dívida estrutural):** amplifica o risco acima e dificulta manutenção; tratar em seguida.

| # | Severidade | Arquivo | Tema |
|---|-----------|---------|------|
| 1 | P0 | `routes/users_routes.py:58` | Auto-registro como admin |
| 2 | P0 | `routes/cart_routes.py:18` | Carrinho sem auth (IDOR) |
| 3 | P0 | `routes/order_routes.py:16` | Pedidos sem auth (IDOR + estoque) |
| 4 | P0 | `controllers/favorites_controller.py:39` | Favoritos por header falsificável |
| 5 | P0 | `services/jwt_service.py:224` | `owner_or_admin_required` nega o dono (str vs int) |
| 6 | P0 | `services/jwt_service.py:257` | Refresh de token sempre falha (str vs int) |
| 7 | P0 | `services/jwt_service.py:15` | `JWT_SECRET_KEY` com fallback público |
| 8 | P0 | `controllers/users_controller.py:742` | Exclusão de conta sem auth e força-brutável |
| 9 | P0 | `routes/categories_routes.py:17` | CRUD de categorias sem `@admin_required` |
| 10 | P0 | `routes/images_routes.py:17` | Upload/delete de imagens sem auth |
| 11 | P1 | `controllers/order_controller.py:105` | Cobrança multiplicada por `quantity` (viola peça única) |
| 12 | P1 | `controllers/order_controller.py:101` | Pedido com total 0 aceito |
| 13 | P1 | `controllers/cart_controller.py:96` | Injeção de operador NoSQL |
| 14 | P1 | `models/user_model.py:358` | Admin padrão com senha fraca |
| 15 | P0 | `services/jwt_service.py:177` | Privilégio obsoleto na claim do token |

---

## P0 — Segurança / autenticação

### 1. Auto-registro como administrador
- **Local:** `backend/app/routes/users_routes.py:58` (rota) + `backend/app/models/user_model.py:238-239` (`prepare_new_user`)
- **Problema:** `POST /api/users/` é público e `validate_user_payload`/`prepare_new_user` aceitam `tipo:"Administrador"` diretamente do payload. `prepare_new_user` marca admin como `ativo=True` e `email_confirmado=True` na hora.
- **Impacto:** qualquer anônimo cria uma conta admin totalmente funcional e passa em `admin_required` em todos os endpoints de gestão.
- **Correção sugerida:** no registro público, forçar `tipo="Cliente"` (ignorar/rejeitar `tipo` do payload). Criação de admin só via endpoint protegido por `@admin_required`.
- [ ] Corrigido

### 2. Rotas de carrinho sem autenticação (IDOR)
- **Local:** `backend/app/routes/cart_routes.py:18-51`
- **Problema:** nenhuma rota de carrinho aplica decorator de auth; o usuário é identificado só pelo `<int:user_id>` da URL.
- **Impacto:** `GET /api/cart/42` lê o carrinho de qualquer um; `POST .../add`, `PUT .../update`, `DELETE .../clear` alteram carrinho alheio.
- **Correção sugerida:** aplicar `@owner_or_admin_required('user_id')` (após corrigir o item 5) em todas as rotas de carrinho.
- [ ] Corrigido

### 3. Rotas de pedido sem autenticação (IDOR + manipulação de estoque)
- **Local:** `backend/app/routes/order_routes.py:16-43`
- **Problema:** todas as rotas de pedido são públicas.
- **Impacto:** criar pedido "confirmado" para qualquer `user_id` (marca produtos como `vendido`); `POST /api/orders/<id>/cancel` reverte vendas (`vendido` → `disponivel`, `order_controller.py:253-257`); `GET /api/orders/<id>` expõe endereço/PII do dono; `PUT /api/orders/<id>/status` permite marcar como `entregue`.
- **Correção sugerida:** `@owner_or_admin_required('user_id')` nas rotas de usuário; `@admin_required` em `update_order_status`; ownership + `@jwt_required` em `get_order_by_id`/`cancel`.
- [ ] Corrigido

### 4. Favoritos autenticados por header falsificável
- **Local:** `backend/app/controllers/favorites_controller.py:34-46`
- **Problema:** `require_auth` lê `X-User-Id` em texto puro como identidade, sem validar JWT.
- **Impacto:** `curl -H 'X-User-Id: 7' /api/favorites` lista/modifica favoritos de qualquer usuário. Contradiz a regra do CLAUDE.md: _"Auth via header `Authorization: Bearer <token>`"_.
- **Correção sugerida:** remover `require_auth`; usar `@jwt_required` e ler a identidade de `g.user_id`.
- [ ] Corrigido

### 5. `owner_or_admin_required` nega o próprio dono (bug de tipo str vs int)
- **Local:** `backend/app/services/jwt_service.py:224` (e origem em `:35`)
- **Problema:** `sub` é gravado como `str(user_id)` (linha 35), mas o decorator faz `int(resource_user_id)` (linha 220) e compara `g.user_id != resource_user_id`. `'5' != 5` é sempre `True`.
- **Impacto:** nenhum não-admin acessa o próprio perfil/atualização/troca de senha — todos recebem 403. Quebra usuários legítimos.
- **Correção sugerida:** padronizar o tipo. Ex.: comparar como string (`str(resource_user_id)`) ou converter `g.user_id = int(payload['sub'])` de forma consistente em `jwt_required`/`admin_required`/`owner_or_admin_required`. **Escolher UMA convenção e aplicar em todo o serviço** (ver também item 6).
- [x] Corrigido — convenção `int` via helper `get_user_id_from_payload`

### 6. Refresh de token sempre falha (mesmo bug str vs int)
- **Local:** `backend/app/services/jwt_service.py:257`
- **Problema:** `find_one({'id': user_id})` com `user_id = payload['sub']` (string), mas o `id` é armazenado como `int` (`user_model.py` schema `:73-76`). A busca nunca casa.
- **Impacto:** `POST /api/users/refresh-token` sempre retorna 401 "Usuário não encontrado"; refresh quebrado para todos, forçando novo login ao expirar o access token de 24h.
- **Correção sugerida:** `find_one({'id': int(user_id)})` (ou converter na convenção única do item 5).
- [x] Corrigido — `sub` normalizado para `int` antes do `find_one`

### 7. `JWT_SECRET_KEY` com fallback público
- **Local:** `backend/app/services/jwt_service.py:15`
- **Problema:** fallback para a constante `'luxus-brecho-secret-key-change-in-production'` quando a env var não está definida.
- **Impacto:** deploy sem `JWT_SECRET_KEY` assina com uma chave do repositório → tokens de admin forjáveis por qualquer um que leia o código.
- **Correção sugerida:** falhar rápido no startup se `JWT_SECRET_KEY` estiver ausente (sem default). Idealmente centralizar num módulo de config validado.
- [x] Corrigido — `RuntimeError` no import se a env var estiver ausente

### 8. Exclusão de conta sem auth e força-brutável
- **Local:** `backend/app/controllers/users_controller.py:742` (`confirm_account_deletion`) + rotas `users_routes.py:142-143`
- **Problema:** endpoint não autenticado, lê `user_id` do corpo, compara código de 6 dígitos (`!=`) sem limite de tentativas e sem rate limit (essas rotas não estão no conjunto limitado). `int(user_id)` também gera 500 para entrada não numérica.
- **Impacto:** atacante dispara `request-deletion` para a vítima e itera `000000..999999` na janela de 30 min → `delete_one` apaga a conta.
- **Correção sugerida:** exigir `@jwt_required` + ownership; aplicar rate limit e contador de tentativas (invalidar código após N falhas); comparar de forma constante; validar `user_id` numérico com retorno 400.
- [ ] Corrigido

### 9. CRUD de categorias sem `@admin_required`
- **Local:** `backend/app/routes/categories_routes.py:17-22`
- **Problema:** `create/update/delete/activate` de categoria não têm gate de admin, ao contrário do CRUD de produtos (`products_routes.py:105`).
- **Impacto:** anônimo cria/apaga categorias.
- **Correção sugerida:** aplicar `@admin_required` nessas rotas.
- [ ] Corrigido

### 10. Upload/delete de imagens sem autenticação
- **Local:** `backend/app/routes/images_routes.py:17-23`
- **Problema:** `upload`, `upload-multiple` e `delete` sem decorator de auth.
- **Impacto:** anônimo envia arquivos arbitrários ao Supabase (abuso de storage/custo) ou remove imagens de produtos existentes.
- **Correção sugerida:** `@admin_required` nas rotas de mutação de imagem.
- [ ] Corrigido

### 15. Privilégio obsoleto na claim do token
- **Local:** `backend/app/services/jwt_service.py:177`
- **Problema:** `admin_required` confia na claim `type` do próprio token em vez de reler o papel do banco; `jwt_required` nunca verifica `ativo`.
- **Impacto:** admin rebaixado para `Cliente` ou desativado mantém privilégios por até 24h; conta desativada continua autenticando.
- **Correção sugerida:** reler `tipo`/`ativo` do banco nos decorators sensíveis (custo de 1 query) ou usar tokens de vida curta + invalidação. Avaliar trade-off latência × frescor.
- [ ] Corrigido

---

## P1 — Correção / regras de domínio

### 11. Cobrança multiplicada por `quantity` (viola regra de peça única)
- **Local:** `backend/app/controllers/order_controller.py:105` (e `cart_controller.py:124`, `:235`)
- **Problema:** `item_total = preco * item.get('quantity', 1)` e o pedido grava `quantity`, mas o produto é marcado `vendido` só uma vez. `add_to_cart` também **incrementa** a quantidade ao re-adicionar.
- **Regra violada (CLAUDE.md):** _"Cada produto é uma peça única: o carrinho não tem quantidade por item — um produto está ou não no carrinho."_
- **Impacto:** cliente envia `quantity:3` de uma peça única → cobrado 3× por um item que existe uma vez; total do pedido e estoque divergem.
- **Correção sugerida:** remover `quantity` do modelo de carrinho/pedido; tratar "add" como idempotente; total = soma de `preco` dos produtos. Remover `update_cart_item` (`cart_controller.py:208`).
- [ ] Corrigido

### 12. Pedido com total 0 aceito silenciosamente
- **Local:** `backend/app/controllers/order_controller.py:99-115`
- **Problema:** itens com `product_id` inexistente são pulados (`if product:`), sem erro. Se todos forem inválidos, `items_with_details=[]` e `total=0`, mas o pedido é criado com status `confirmado` e retorna 201.
- **Impacto:** pedidos vazios/subfaturados criados sem falha visível.
- **Correção sugerida:** se algum `product_id` do payload não resolver, retornar 400 (ou 404); rejeitar pedido com 0 itens válidos.
- [ ] Corrigido

### 13. Injeção de operador NoSQL
- **Local:** `backend/app/controllers/cart_controller.py:96` (e `create_order`, `sync_cart`)
- **Problema:** `product_id` cru do payload vai direto ao filtro do Mongo. O guard `if not product_id` só rejeita falsy; `{"$gt": 0}` é truthy.
- **Impacto:** `{"product_id": {"$gt": 0}}` casa produto arbitrário e o objeto-operador é gravado como `product_id` no carrinho.
- **Correção sugerida:** validar que `product_id` é `int` antes de qualquer query (reaproveitar `validate_favorite_payload`/`validate_cart_item`).
- [ ] Corrigido

### 14. Admin padrão com senha fraca e log enganoso
- **Local:** `backend/app/models/user_model.py:344-374`
- **Problema:** `create_default_admin` semeia `contatojmfr@gmail.com` / `senha123` em todo banco novo; o log de sucesso imprime credenciais falsas (`admin@luxusbrecho.com` / `admin123`).
- **Impacto:** qualquer um que leia o repositório entra como administrador; o log dificulta a rotação real.
- **Correção sugerida:** gerar senha aleatória forte (ou exigir via env var no primeiro boot) e corrigir o log para refletir as credenciais reais — ou remover o seed de admin do código.
- [ ] Corrigido

---

## P2 — Dívida estrutural (amplifica o risco acima)

- [ ] **`products_controller.py` é código morto e divergente.** `products_routes.py` reimplementa tudo inline; as cópias já divergiram (`$facet` com projeção no controller vs. `find`+`count_documents` na rota registrada). Correções aplicadas no controller nunca entram em produção. → Manter uma implementação só (controller fino) e apagar a duplicata.
- [ ] **Segunda `create_app()` obsoleta** em `controllers/__init__.py:5` com `DEBUG=True`, nome de banco fixo (`luxus_brecho`), `app.mongo` apontando para o database (não o client) e só 2 blueprints. Sombra perigosa da factory real. → Deixar `controllers/__init__.py` como marcador de pacote vazio.
- [ ] **Guard `db is None` copiado ~45 vezes** com 3 variações de mensagem. → Centralizar num `@app.before_request` ou decorator `require_db`, retornando um 503 canônico.
- [ ] **Duplicação de helpers:** `_serialize` (6 cópias, uma expondo `_id` cru), `get_next_id`/`get_next_sequence` (4 cópias contra a mesma coleção `counters`), parsing de paginação (6 cópias — `list_users` sem clamp permite `page_size` ilimitado). → Extrair para `utils/`.
- [ ] **Rate limiter em `memory://`** (`__init__.py:97`) — em múltiplos workers/serverless (Vercel) os contadores multiplicam e zeram a cada restart, enfraquecendo brute-force no login. → Usar storage compartilhado (Redis) em produção.
- [ ] **Eficiência:** `create_order` faz N+1 (um `find_one`/`update_one` por item → usar `$in` + `update_many`); `create_product_with_image` faz **upload duplo sempre** (o `temp_id` de timestamp nunca é igual ao id sequencial → obter o id real antes e subir uma vez); SMTP síncrono no caminho da requisição (signup/confirmação/reset → enviar assíncrono); lookups por `token_confirmacao`/`reset_token` sem índice (full scan → adicionar índices esparsos).
- [ ] **Registro de blueprints engole `ImportError`** (`__init__.py:255`) — um erro num arquivo de rotas remove a feature inteira em silêncio (só um `print`). → Falhar rápido no startup para blueprints obrigatórios.
- [ ] **Respostas JSON sem o campo `success`** — os controllers omitem sistematicamente `success` (regra do CLAUDE.md: _"Respostas JSON seguem o padrão `{ "success": bool, "message": str, ... }`"_). → Padronizar o formato de resposta.
- [ ] **Regex injection / ReDoS em `list_users`** (`users_controller.py:60-64`) — `{"$regex": search}` com input não escapado (exploração limitada a admin autenticado). → Escapar o termo ou usar índice de texto.

---

## Ordem de implementação sugerida

1. **Corrigir o bug de tipo str/int (itens 5 e 6)** — destrava o fluxo de auth legítimo e é baixo risco. Definir a convenção única de tipo do `sub`.
2. **Aplicar decorators de auth nas rotas desprotegidas (itens 2, 3, 4, 9, 10)** — reusa o mecanismo já existente em `jwt_service`.
3. **Fechar o auto-registro de admin e a exclusão de conta (itens 1, 8).**
4. **Endurecer o `JWT_SECRET_KEY` e o admin padrão (itens 7, 14).**
5. **Regra de peça única e validações de pedido/carrinho (itens 11, 12, 13).**
6. **Frescor de privilégio (item 15)** e, em seguida, a dívida estrutural (P2).
