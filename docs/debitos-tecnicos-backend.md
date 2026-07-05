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

Aplicada a fatia que **não muda o contrato observável consumido por frontend e
mobile** (os clientes continuam funcionando), com a suíte `pytest` verde
(100 passando). O que altera contrato de cliente ficou para PRs coordenados.

| Item | Status | Observação |
|------|--------|------------|
| 1 — Autorização | 🟡 parcial | **Feito:** escrita de `categories` agora exige `@admin_required`. **Pendente:** JWT em `cart`/`orders`/`favorites` (quebra o mobile, que hoje nem tem JWT real — precisa de PR coordenado nos 3 apps). |
| 2 — Envelope de resposta | 🔴 pendente | Muda o corpo consumido por frontend/mobile; exige varredura conjunta. Não iniciado. |
| 3 — Boilerplate (`@require_db` + errorhandler) | 🟢 feito | Criado `@require_db` (`app/utils/decorators.py`) e `@app.errorhandler(Exception)` central. `try/except` genérico removido de `cart`/`orders`; **mantido** em `users`/`images` por serem fluxos sensíveis (o handler central já é a rede de segurança). |
| 4 — Duplicação de infraestrutura | 🟢 feito | Extraídos `serialize_doc`, `next_sequence`, `get_pagination_params` e `_render_email` para `app/utils/`. `favorites` mantém `_id`→string (divergência do item 4 deixada para o PR do envelope). |

> **Bloqueador do item 1 descoberto na implementação:** o app **mobile não usa
> JWT real** — grava a string literal `'authenticated'` e nunca envia
> `Authorization`. Exigir `@jwt_required` em cart/orders/favorites quebra o
> mobile até um overhaul do auth dele. Por isso o núcleo do item 1 permanece
> como PR coordenado, e não foi aplicado aqui.

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

1. **Item 1 (autorização)** — é segurança, não estética. Vem primeiro.
2. **Item 3 (`@require_db` + errorhandler)** — só depois de ter `pytest`
   rodando, pelo volume de pontos tocados.
3. **Item 4 (helpers compartilhados)** — incremental, um helper por PR.
4. **Item 2 (envelope de resposta)** — o mais acoplado ao cliente; encaixar no
   mesmo esforço de padronização do item 4, por domínio.
