# Plano de Desenvolvimento — Correções do Backend

> **Base:** [`code-review-backend.md`](./code-review-backend.md)
> **Branch:** `fix/backend-code-review`
> **Data:** 2026-07-01
> **Validação:** os 15 itens numerados e a dívida estrutural (P2) foram reconferidos lendo o código atual desta branch. Todos os problemas continuam presentes; os números de linha do review batem.
> **Ordenação:** da correção mais crítica (explorável hoje por anônimo) para a mais leve (dívida estrutural). Respeita dependências técnicas — por isso a convenção de tipo do JWT (itens 5/6) vem antes de aplicar os decorators de posse.

## Como usar este plano

Cada fase é um bloco entregável e testável isoladamente. Faça **uma fase por PR** (ou por commit lógico), rodando os testes de fumaça descritos ao final de cada uma. Marque os checkboxes conforme concluir. As fases estão em ordem de execução recomendada — não pule a Fase 1, pois ela destrava o fluxo de auth legítimo e é pré-requisito das Fases 2 e 3.

**Convenção de referência:** cada item cita o número correspondente no review (`[#N]`).

---

## Fase 1 — Fundação de autenticação (destrava tudo) 🔴 P0

> Sem esta fase, aplicar os decorators de posse nas rotas abertas (Fase 2) **tranca até os donos legítimos**. É o alicerce.

### 1.1 — Unificar a convenção de tipo do `sub` (int em todo o serviço) `[#5, #6]`
- **Arquivo:** `backend/app/services/jwt_service.py`
- **Raiz:** o token grava `sub = str(user_id)` (linha 35/57), mas o banco guarda `id` como `int`. Isso quebra duas coisas: `owner_or_admin_required` compara `'5' != 5` → sempre 403 para o dono (linha 224); `refresh_access_token` faz `find_one({'id': '5'})` → nunca casa → refresh sempre 401 (linha 257).
- **Decisão de convenção:** normalizar para **`int`** no ponto de leitura do token.
- **Passos:**
  1. Em `jwt_required`, `admin_required` e `owner_or_admin_required`, trocar `g.user_id = payload.get('sub')` por conversão segura para int (ex.: `g.user_id = int(payload['sub'])` dentro de try/except → 401 se inválido).
  2. Em `owner_or_admin_required`, garantir que `resource_user_id` também é int (já há `int()` na linha 220) e comparar `g.user_id != resource_user_id` com ambos int.
  3. Em `refresh_access_token`, trocar `find_one({'id': user_id})` por `find_one({'id': int(user_id)})`.
- **Critério de aceite:** um Cliente logado consegue `GET /api/users/<seu_id>` (200, não 403); `POST /api/users/refresh-token` devolve novos tokens (200, não 401).
- [ ] Concluído

### 1.2 — `JWT_SECRET_KEY` sem fallback público (fail-fast) `[#7]`
- **Arquivo:** `backend/app/services/jwt_service.py:15`
- **Problema:** fallback para `'luxus-brecho-secret-key-change-in-production'` — quem lê o repositório forja tokens de admin.
- **Passos:**
  1. Remover o default. Ler `os.environ['JWT_SECRET_KEY']` e, se ausente, lançar `RuntimeError` no import/startup.
  2. Confirmar que `JWT_SECRET_KEY` está no `.env`/variáveis do ambiente de deploy (Vercel) e no `.env.example`.
- **Critério de aceite:** app não sobe sem `JWT_SECRET_KEY` definido; nenhuma string de segredo hardcoded no código.
- [ ] Concluído

**Teste de fumaça da Fase 1:** login → acesso ao próprio perfil → refresh-token, todos 200.

---

## Fase 2 — Fechar rotas abertas / IDOR 🔴 P0

> Reusa o mecanismo de `jwt_service` já corrigido na Fase 1. É a maior redução de superfície de ataque.

### 2.1 — Favoritos: trocar header falsificável por JWT `[#4]`
- **Arquivos:** `backend/app/controllers/favorites_controller.py:34-46` (`require_auth`), `backend/app/routes/favorites_routes.py`, `backend/app/__init__.py:130` (CORS).
- **Problema:** `require_auth` lê `X-User-Id` em texto puro como identidade. `curl -H 'X-User-Id: 7'` assume qualquer conta.
- **Passos:**
  1. Remover o decorator `require_auth`; aplicar `@jwt_required` nas rotas de favoritos.
  2. Ler a identidade de `g.user_id` (não mais do parâmetro/header). Ajustar as assinaturas das funções do controller que hoje recebem `user_id` do header.
  3. Remover `'X-User-Id'` de `allow_headers` no CORS (`__init__.py:130`) — deixa de ser um header aceito.
- **Critério de aceite:** requisição sem `Authorization` → 401; com token de A, só mexe nos favoritos de A.
- [ ] Concluído

### 2.2 — Carrinho: aplicar posse em todas as rotas `[#2]`
- **Arquivo:** `backend/app/routes/cart_routes.py:18-51`
- **Passos:** aplicar `@owner_or_admin_required('user_id')` em `get`, `add`, `remove`, `update`, `clear`, `sync`. (Depende da Fase 1.1.)
- **Critério de aceite:** `GET /api/cart/42` com token de outro usuário → 403; com token do 42 → 200.
- [ ] Concluído

### 2.3 — Pedidos: posse nas rotas de usuário, admin no status `[#3]`
- **Arquivo:** `backend/app/routes/order_routes.py:16-43`
- **Passos:**
  1. `@owner_or_admin_required('user_id')` em `get_user_orders` e `create_order` (rotas `/user/<int:user_id>`).
  2. `@admin_required` em `update_order_status` (`/<int:order_id>/status`).
  3. `get_order_by_id` e `cancel_order` recebem `order_id`, não `user_id` — proteger com `@jwt_required` e validar posse dentro do controller (carregar o pedido, comparar `order['user_id']` com `g.user_id`, senão 403). Admin ignora a checagem.
- **Critério de aceite:** anônimo não cria pedido; não-dono não vê/cancela pedido alheio; só admin altera status.
- [ ] Concluído

### 2.4 — Categorias: exigir admin no CRUD `[#9]`
- **Arquivo:** `backend/app/routes/categories_routes.py:17-22`
- **Passos:** aplicar `@admin_required` em `create`, `update`, `delete`, `activate`. Manter `list`/`get`/`summary` públicos (leitura). Como as rotas usam o estilo `bp.route(...)(func)`, envolver com o decorator ou migrar para funções decoradas.
- **Critério de aceite:** anônimo recebe 401/403 ao criar/apagar categoria.
- [ ] Concluído

### 2.5 — Imagens: exigir admin nas mutações `[#10]`
- **Arquivo:** `backend/app/routes/images_routes.py:17-23`
- **Passos:** `@admin_required` em `upload`, `upload-multiple`, `delete`. Leitura (`list`, `info`) pode continuar pública.
- **Critério de aceite:** anônimo não envia/apaga imagem no Supabase.
- [ ] Concluído

**Teste de fumaça da Fase 2:** para cada recurso, repetir o par (sem token → 401) e (token de outro usuário → 403).

---

## Fase 3 — Bloquear escalada de privilégio 🔴 P0

### 3.1 — Fechar o auto-registro como administrador `[#1]`
- **Arquivos:** `backend/app/controllers/users_controller.py:111` (`create_user`), `backend/app/models/user_model.py:225-244` (`prepare_new_user`).
- **Problema:** `POST /api/users/` é público e aceita `tipo:"Administrador"` do payload; `prepare_new_user` marca admin como `ativo=True`/`email_confirmado=True` na hora.
- **Passos:**
  1. No registro público, **forçar `tipo="Cliente"`** — ignorar/rejeitar `tipo` vindo do payload.
  2. Criar um caminho separado de criação de admin somente sob `@admin_required` (novo endpoint ou flag interna).
- **Critério de aceite:** `POST /api/users/` com `tipo:"Administrador"` cria um Cliente comum (não admin).
- [ ] Concluído

### 3.2 — Endurecer a exclusão de conta `[#8]`
- **Arquivos:** `backend/app/controllers/users_controller.py:686` (`request_account_deletion`), `:742` (`confirm_account_deletion`), `backend/app/routes/users_routes.py:142-143`.
- **Problemas:** rotas sem auth; `user_id` vem do corpo; código de 6 dígitos comparado com `!=` sem limite de tentativas nem rate limit; `int(user_id)` cru gera 500 para entrada não numérica.
- **Passos:**
  1. Exigir `@jwt_required` + posse (ler o alvo de `g.user_id`, não do corpo).
  2. Aplicar rate limit (reusar o helper `_apply_rate_limit`/`limiter.limit` já usado nas rotas de auth) nas duas rotas.
  3. Contador de tentativas: invalidar o `deletion_code` após N falhas.
  4. Comparação em tempo constante (`secrets.compare_digest`).
  5. Validar `user_id` numérico e retornar 400 (não deixar estourar 500).
- **Critério de aceite:** anônimo não dispara/consome exclusão; código é invalidado após N erros; entrada não numérica → 400.
- [ ] Concluído

### 3.3 — Frescor de privilégio nos decorators sensíveis `[#15]`
- **Arquivo:** `backend/app/services/jwt_service.py:157-187` (`admin_required`) e `:97-124` (`jwt_required`).
- **Problema:** `admin_required` confia na claim `type` do token; `jwt_required` nunca checa `ativo`. Admin rebaixado ou conta desativada mantêm acesso por até 24h.
- **Passos:** reler `tipo`/`ativo` do banco (1 query) nos decorators sensíveis e negar se `ativo=False` ou papel divergente. Avaliar o trade-off latência × frescor (alternativa: tokens de vida curta).
- **Critério de aceite:** desativar um usuário no banco invalida o acesso na próxima requisição; rebaixar um admin remove o privilégio imediatamente.
- [ ] Concluído

---

## Fase 4 — Segredos e seed inseguros 🔴 P0

### 4.1 — Admin padrão com senha forte e log correto `[#14]`
- **Arquivo:** `backend/app/models/user_model.py:344-378` (`create_default_admin`).
- **Problemas:** semeia `contatojmfr@gmail.com` / `senha123` em todo banco novo; o log de sucesso imprime credenciais **falsas** (`admin@luxusbrecho.com` / `admin123`), dificultando a rotação.
- **Passos (escolher UMA opção):**
  - **(a)** Gerar senha aleatória forte no primeiro boot e exibi-la uma única vez; ou
  - **(b)** Exigir `ADMIN_EMAIL`/`ADMIN_PASSWORD` via env var, sem default; ou
  - **(c)** Remover o seed do código e criar o admin por script/CLI fora do repositório.
  - Em qualquer caso, **corrigir o log** para refletir as credenciais reais.
- **Critério de aceite:** nenhuma credencial de admin utilizável está hardcoded; o log não mente sobre e-mail/senha.
- [ ] Concluído

---

## Fase 5 — Regras de domínio / correção 🟠 P1

### 5.1 — Regra de peça única: remover `quantity` `[#11]`
- **Arquivos:** `backend/app/controllers/order_controller.py:105`, `backend/app/controllers/cart_controller.py:118-155` (`add_to_cart` incrementa), `:208-252` (`update_cart_item`).
- **Regra (CLAUDE.md):** cada produto é peça única — o carrinho não tem quantidade por item.
- **Problema:** `item_total = preco * quantity` cobra 3× por `quantity:3`; `add_to_cart` incrementa ao re-adicionar; produto é marcado `vendido` uma vez só → total e estoque divergem.
- **Passos:**
  1. Remover `quantity` do modelo de carrinho e de pedido; tratar "add" como **idempotente** (produto está ou não no carrinho).
  2. `total` = soma dos `preco` dos produtos.
  3. Remover `update_cart_item` e sua rota (`cart_routes.py:36-39`).
- **Critério de aceite:** re-adicionar o mesmo produto não duplica; total do pedido = soma dos preços únicos.
- [ ] Concluído

### 5.2 — Rejeitar pedido com itens inválidos / total zero `[#12]`
- **Arquivo:** `backend/app/controllers/order_controller.py:99-115`.
- **Problema:** `if product:` pula silenciosamente `product_id` inexistente; se todos forem inválidos, cria pedido `confirmado` com `total=0` e retorna 201.
- **Passos:** se qualquer `product_id` do payload não resolver → 400/404; rejeitar pedido com 0 itens válidos.
- **Critério de aceite:** payload só com IDs inválidos → erro (não 201); nenhum pedido de total 0 é persistido.
- [ ] Concluído

### 5.3 — Bloquear injeção de operador NoSQL `[#13]`
- **Arquivos:** `backend/app/controllers/cart_controller.py:88-96` (`add_to_cart`), e também `create_order`/`sync_cart` que usam `product_id` cru.
- **Problema:** `if not product_id` só rejeita falsy; `{"$gt": 0}` é truthy e vai direto ao filtro do Mongo, casando produto arbitrário e sendo gravado como `product_id`.
- **Passos:** validar que `product_id` é `int` antes de qualquer query (reusar `validate_cart_item`/`validate_favorite_payload`); rejeitar não-int com 400.
- **Critério de aceite:** `product_id: {"$gt": 0}` → 400; só inteiros são aceitos.
- [ ] Concluído

---

## Fase 6 — Dívida estrutural 🟡 P2

> Amplifica o risco das fases anteriores e dificulta manutenção. Tratar após os P0/P1. Podem virar issues separadas.

- [ ] **Remover a segunda `create_app()` obsoleta** (`controllers/__init__.py`) — hoje tem `DEBUG=True`, banco fixo `luxus_brecho`, `app.mongo` apontando para o database (não o client) e só 2 blueprints. É uma sombra perigosa da factory real. Deixar o arquivo como marcador de pacote vazio.
- [ ] **Eliminar código morto de `products_controller.py`** — `products_routes.py` reimplementa tudo inline e as cópias já divergiram. Manter uma implementação só (controller fino) e apagar a duplicata.
- [ ] **Centralizar o guard `db is None`** (copiado ~45×, com 3 mensagens diferentes) num `@app.before_request` ou decorator `require_db`, retornando 503 canônico.
- [ ] **Extrair helpers duplicados para `utils/`:** `_serialize` (6 cópias, uma expõe `_id` cru), `get_next_id`/`get_next_sequence` (4 cópias), parsing de paginação (6 cópias — `list_users` sem clamp permite `page_size` ilimitado, `users_controller.py:43-44`).
- [ ] **Rate limiter fora de `memory://`** (`__init__.py:97`) — em múltiplos workers/serverless (Vercel) os contadores multiplicam e zeram a cada restart, enfraquecendo a proteção de brute-force do login. Usar storage compartilhado (Redis) em produção.
- [ ] **Eficiência:** `create_order` faz N+1 (usar `$in` + `update_many`); `create_product_with_image` faz upload duplo sempre (obter o id sequencial real antes e subir uma vez); SMTP síncrono no caminho da requisição (signup/confirmação/reset → enviar assíncrono); lookups por `token_confirmacao`/`reset_token` sem índice (adicionar índices esparsos).
- [ ] **Registro de blueprints não deve engolir `ImportError`** (`__init__.py:255`) — hoje um erro num arquivo de rotas remove a feature inteira só com um `print`. Falhar rápido no startup para blueprints obrigatórios.
- [ ] **Padronizar respostas com o campo `success`** — os controllers omitem `success` sistematicamente, contrariando o padrão do CLAUDE.md (`{ "success": bool, "message": str, ... }`).
- [ ] **Escapar/tratar regex em `list_users`** (`users_controller.py:60-64`) — `{"$regex": search}` com input não escapado permite ReDoS (exploração limitada a admin autenticado). Escapar o termo ou usar índice de texto.

---

## Resumo da ordem de execução

| Fase | Foco | Itens do review | Severidade |
|------|------|-----------------|------------|
| 1 | Fundação de auth (tipo do JWT + segredo) | 5, 6, 7 | 🔴 P0 |
| 2 | Fechar rotas abertas / IDOR | 4, 2, 3, 9, 10 | 🔴 P0 |
| 3 | Bloquear escalada de privilégio | 1, 8, 15 | 🔴 P0 |
| 4 | Segredos e seed inseguros | 14 | 🔴 P0 |
| 5 | Regras de domínio | 11, 12, 13 | 🟠 P1 |
| 6 | Dívida estrutural | (lista P2) | 🟡 P2 |

**Regra de ouro:** Fase 1 primeiro (destrava e é pré-requisito), depois 2→3→4 antes de qualquer deploy público, e só então 5→6.
