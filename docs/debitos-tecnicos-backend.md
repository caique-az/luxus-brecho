# Débitos técnicos — Backend

Registro dos itens identificados durante a revisão de qualidade do backend
(`/simplify`, jul/2026) que **não** foram aplicados junto com a limpeza porque
mudam comportamento observável, tocam muitos pontos de uma vez ou envolvem
decisão de segurança. Cada um merece um PR próprio, revisado com atenção.

A limpeza segura (código morto, otimizações de query, simplificações sem efeito
observável) já foi aplicada na `develop` no commit `refactor(backend): remove
código morto e otimiza acesso ao MongoDB`. Este documento é o backlog do que
sobrou.

> Contexto de altitude: o tema comum aos quatro itens é o mesmo — a
> infraestrutura compartilhada certa frequentemente **já existe** (decorators do
> `jwt_service`, errorhandlers em `create_app`, `normalize_*` nos models), mas é
> contornada por casos especiais empilhados endpoint a endpoint. A correção de
> fundo é passar a usar (ou criar) **uma única camada** para auth, resposta,
> guarda de banco e serialização, em vez de reimplementar em cada função.

## Status da implementação (jul/2026)

Os quatro itens foram aplicados com a suíte `pytest` verde (113 passando). O
item 2 foi feito de forma **aditiva** — só acrescenta `success`, mantendo as
chaves já consumidas por frontend e mobile —, então nenhum cliente quebra e não
foi preciso o deploy coordenado que se temia.

| Item | Status | Observação |
|------|--------|------------|
| 1 — Autorização | 🟢 feito | `cart`, `orders` e `favorites` agora exigem **JWT** com identidade em `g.user_id` (dono-ou-admin); `X-User-Id`/`require_auth` removidos; escrita de `categories` exige admin. Corrigidos 2 bugs str-vs-int (`owner_or_admin_required` e `refresh_access_token`). Coordenado com mobile (JWT real) e frontend (Pedidos/Checkout via axios). |
| 2 — Envelope de resposta | 🟢 feito | Helpers `ok()`/`err()` em `app/utils/responses.py`; todo controller/rota emite o envelope **plano** `{success, ...}`. **Aditivo**: só acrescenta `success` e mantém as chaves de domínio, logo os clientes seguem funcionando. Normalizados os `{error}` divergentes de `images_controller` **e dos decorators JWT** → `message` (frontend `api.js` ajustado). Listas puras (`/categories/summary`) ficam como exceção documentada. Contrato travado em `tests/test_envelope.py`. |
| 3 — Boilerplate (`@require_db` + errorhandler) | 🟢 feito | Criado `@require_db` (`app/utils/decorators.py`) e `@app.errorhandler(Exception)` central. `try/except` genérico removido de `cart`/`orders`; **mantido** em `users`/`images` por serem fluxos sensíveis (o handler central já é a rede de segurança). |
| 4 — Duplicação de infraestrutura | 🟢 feito | Extraídos `serialize_doc`, `next_sequence`, `get_pagination_params` e `_render_email` para `app/utils/`. `favorites` ainda mantém `_id`→string — resíduo do item 4 (o `_id` não deveria vazar), **ortogonal ao envelope** e sem cliente que o consuma; deixado para um PR próprio de serialização. |

> **Item 1 — coordenação de 3 apps.** O mobile não tinha JWT real (gravava a
> string `'authenticated'`); foi refeito para armazenar/enviar o token
> (`feat(mobile): usa JWT real`). O frontend migrou Pedidos/Checkout para a
> instância axios que injeta o Bearer. Só então o backend passou a exigir JWT
> nesses fluxos. Ordem de deploy: publicar clientes antes do backend.

---

## 1. Autorização inconsistente (⚠️ segurança — prioridade máxima)

**Problema.** Coexistem três esquemas de autorização, escolhidos caso a caso por
domínio, e dois deles são inseguros:

| Domínio | Esquema atual | Situação |
|---------|---------------|----------|
| `products` (escrita), `users` | Decorators JWT (`@admin_required`, `@owner_or_admin_required`) | Correto |
| `favorites` | Header `X-User-Id` (decorator `require_auth` local) | **Forjável** — qualquer valor no header é aceito como identidade |
| `cart`, `orders` | Nenhum | `GET/POST /api/cart/<user_id>`, `POST /api/orders/user/<user_id>` e cancelar pedido aceitam qualquer `user_id` na URL |
| `categories` (escrita) | Nenhum | `POST/PUT/DELETE` sem `@admin_required`, ao contrário do CRUD equivalente de `products` |

**Impacto.** Superfície de acesso quebrada: é possível ler/editar o carrinho e
criar/cancelar pedidos de terceiros informando outro `user_id`; favoritos
confiam num header trivialmente falsificável; qualquer cliente altera o catálogo
de categorias. A identidade derivada do token (`g.user_id`) sequer é usada
nesses fluxos — a identidade vem da URL.

**Nota de documentação.** O [`convencoes.md`](./convencoes.md) hoje descreve o
`X-User-Id` de favoritos como convenção intencional. Ao corrigir, atualizar
também esse texto — o header não deve ser tratado como esquema de auth válido.

**Correção proposta.** Unificar tudo no `jwt_service`:
- `cart`, `orders`, `favorites` passam a exigir `@jwt_required`; a identidade do
  dono vem de `g.user_id` (token), **não** de parâmetro de URL, com checagem
  dono-ou-admin.
- Escrita de `categories` recebe `@admin_required`.
- Remover o decorator `require_auth` de `favorites_controller.py`.

**Risco/esforço.** Alto impacto, esforço médio. **Mudança de comportamento**: o
frontend/mobile precisam enviar o `Authorization: Bearer` nesses fluxos (hoje
alguns mandam só o `user_id`); alinhar cliente e backend no mesmo PR ou em PRs
coordenados.

---

## 2. Envelope de resposta `{ success, message }` não seguido

> ✅ **Resolvido.** Helpers `ok()`/`err()` em `app/utils/responses.py`; todos os
> controllers e rotas passam por eles. A migração foi **aditiva** (só acrescenta
> `success`, mantém as chaves de domínio), evitando o deploy coordenado que se
> temia. As chaves `error` de `images_controller` e dos decorators JWT viraram
> `message`. Contrato coberto por `tests/test_envelope.py`. O texto abaixo é o
> diagnóstico original.

**Problema.** O [`convencoes.md`](./convencoes.md) e os errorhandlers de
`create_app` definem o envelope `{ "success": bool, "message": str, ... }`. Na
prática:
- Controllers de sucesso retornam `{ message: ... }` **sem** `success`.
- `images_controller` usa a chave `{ error: ... }` (diferente).
- Os dois endpoints de health retornam formatos distintos entre si.
- `success` só aparece de fato nas respostas de erro geradas pelo framework.

**Impacto.** O cliente não consegue usar `success` como discriminador nem tratar
`message`/`error` de forma uniforme; cada tela acaba tratando cada endpoint de
um jeito.

**Correção proposta.** Helpers centrais de resposta (`ok(payload, status)` /
`err(message, status, errors=None)`) — ou um `JSONProvider` custom — usados por
todos os controllers, e errorhandlers emitindo o mesmo envelope.

**Risco/esforço.** Esforço médio-alto. **Mudança de comportamento**: altera o
corpo das respostas consumidas por frontend e mobile — exige varredura conjunta
nos três apps. Sugestão: padronizar por domínio, um de cada vez, com o cliente
acompanhando.

---

## 3. Boilerplate repetido: guarda de banco e tratamento de erro

**Problema.** Dois padrões colados em quase toda função de controller:
- **Guarda de banco** — `db = current_app.db; if db is None: return
  jsonify(message=...), 503` repetido em ~40 funções, com a mensagem divergindo
  entre endpoints (`"banco de dados indisponível"`, `"database unavailable"`,
  `"Banco de dados indisponível"`).
- **Tratamento de erro** — `try/except Exception → log + 500` reimplementado por
  função, embora `create_app` já registre `@app.errorhandler(500)` e
  `PROPAGATE_EXCEPTIONS=True`. Como cada controller intercepta antes, o handler
  central é anulado — e de forma desigual (as rotas de `products` sem
  `try/except` caem no handler; `users`/`cart`/`orders` não).

**Impacto.** Ruído e indentação extra em dezenas de funções; comportamento de
erro divergente entre endpoints equivalentes; risco de uma função nova esquecer
a guarda e devolver 500 em vez de 503.

**Correção proposta.**
- Um decorator `@require_db` (ou `before_request` que injeta `g.db` e
  curto-circuita com um único 503 padronizado).
- Registrar `@app.errorhandler(Exception)` que loga e devolve o envelope padrão,
  removendo os `try/except` genéricos dos controllers — **mantendo** apenas os
  `except` específicos com semântica própria (ex.: `DuplicateKeyError`).

**Risco/esforço.** Esforço alto pelo número de pontos (~40 funções). Não muda a
resposta em caminho feliz, mas altera o comportamento de erro e a mensagem de
indisponibilidade. **Aplicar com a suíte de testes rodando** (hoje `pytest` não
estava instalado no ambiente de revisão — instalar antes).

---

## 4. Duplicação de infraestrutura compartilhada

**Problema.** Mesma lógica reimplementada em vários pontos:
- **`_serialize`** (`d = dict(doc); d.pop("_id")`) copiado em ~4–5 controllers;
  a serialização de `_id`/`datetime` do Mongo é tratada caso a caso, com regras
  divergentes (uns fazem `pop`, `favorites` converte `_id`→`str`, `cart` faz
  `.isoformat()` campo a campo).
- **Geração de id sequencial** (padrão `counters` com `find_one_and_update`)
  duplicada em 4 models.
- **Parsing de paginação** (`page`/`page_size` com clamp) reescrito em ~6
  controllers, com estilos divergentes (manual vs. `marshmallow` em `products`).
- **Templates de email** — 5 funções em `email_service.py` repetem o mesmo
  esqueleto HTML (header rosa, footer), já com cores divergentes entre si.

**Impacto.** A mesma decisão é tomada em muitos lugares e já derivou; mudanças
(formato de saída, logo do email, regra de paginação) exigem editar N pontos.

**Correção proposta.** Extrair para `app/utils/`: `serialize_doc()` (ou um
`JSONProvider` que trate `ObjectId`/`datetime`), `counters.next_sequence()`,
`pagination.get_params()`, e um `_render_email(inner_html, ...)` único.

**Risco/esforço.** Esforço médio; risco pontual de **mudança de comportamento**
onde as implementações divergem — em especial `favorites`, que hoje devolve
`_id` como string; unificar com o `pop` dos demais **altera a resposta**. Decidir
o formato canônico antes e ajustar o cliente onde necessário.

---

## Priorização sugerida

Ordem em que os itens foram efetivamente atacados (todos concluídos):

1. **Item 1 (autorização)** — segurança, não estética. Veio primeiro.
2. **Item 3 (`@require_db` + errorhandler)** — depois de `pytest` rodando, pelo
   volume de pontos tocados.
3. **Item 4 (helpers compartilhados)** — incremental, um helper por PR.
4. **Item 2 (envelope de resposta)** — resolvido de forma **aditiva** com os
   helpers `ok()`/`err()`, o que dispensou a padronização por domínio com o
   cliente acompanhando que se previa aqui.

### Resíduo em aberto

- **Serialização de `favorites` (`_id` string).** Cauda do item 4: os favoritos
  ainda devolvem `_id` como string em vez de removê-lo como os demais. É
  ortogonal ao envelope e hoje nenhum cliente lê esse campo; fica para um PR
  próprio que unifique a serialização (adotar `serialize_doc`, que faz `pop` do
  `_id`).
