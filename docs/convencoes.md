# Convenções

> Divergências entre o código e estas convenções: [alinhamento-e-debitos.md](./alinhamento-e-debitos.md)

Padrões para manter consistência ao evoluir o projeto. O objetivo é que código novo "se pareça" com o código existente — e que a documentação continue batendo com o código (ver [Convenções de documentação](#convenções-de-documentação)).

## Idioma

- **Domínio em português:** entidades, campos, rotas de pasta e mensagens ao usuário usam PT-BR (`titulo`, `preco`, `Carrinho`, `Favoritos`). Mantenha esse padrão — não traduza campos do MongoDB para inglês.
- **Termos técnicos e identificadores de framework** ficam na forma original (`store`, `controller`, `blueprint`, `useState`).
- Comentários e documentação: português.

## Estrutura de pastas

### Backend — uma responsabilidade por camada
Ao adicionar um recurso novo, crie os arquivos correspondentes em cada camada e **registre o blueprint** na lista `blueprints_to_register` de `app/__init__.py`:

```
app/routes/<recurso>_routes.py          →  blueprint, URLs, decorators de auth
app/controllers/<recurso>_controller.py →  regras de negócio
app/models/<recurso>_model.py           →  acesso ao Mongo + ensure_indexes()
```

Toda validação de entidade vive no model, em funções `validate_*`, `normalize_*` e `prepare_new_*`. Não espalhe regra de negócio pelo controller ou pela rota.

Reuse os helpers canônicos de `app/utils/` em vez de reimplementar: `@require_db` (guard de banco → 503), `serialize_doc` (remove `_id`), `parse_pagination` (clamp de `page`/`page_size`) e o cache de categorias (`utils/cache.py`).

### Frontend — feature co-localizada
Cada página é uma pasta com `index.jsx` + `index.css`:
```
src/pages/<NomeDaPagina>/index.jsx
src/pages/<NomeDaPagina>/index.css
```
Estado global compartilhado → store Zustand em `src/store/`. Chamada de API → wrapper de domínio em `src/services/`, **sempre** sobre a instância axios de `services/api.js` (nunca crie outra instância — ela é quem injeta o token e faz refresh).

### Mobile — rotas por arquivo
Roteamento é o Expo Router: criar `app/nome.tsx` cria a rota `/nome`; `app/(tabs)/x.tsx` é uma aba; `app/recurso/[id].tsx` é rota dinâmica. Configuração nova → `constants/config.ts` exposta por env `EXPO_PUBLIC_*`.

## Padrões de API

- Respostas seguem o envelope **plano** `{ "success": bool, "message": str, ... }`: os dados de domínio ficam no topo, ao lado de `success` (não aninhados sob `data`). Em **controllers, rotas e errorhandlers**, monte sempre com os helpers `ok()` / `err()` de `app/utils/responses.py`, nunca com `jsonify` cru — assim `success` serve de discriminador em todo endpoint e a mensagem de erro fica sempre em `message` (a chave `error` foi abolida, inclusive nos erros de autenticação dos decorators JWT). Erros de validação trazem `errors: { campo: motivo }` (sempre um **dict**; listas de falhas usam outra chave, ex.: `upload_errors`). **Exceções ao envelope:** endpoints que devolvem uma **lista pura** (ex.: `/categories/summary`) e o `GET /api/health`, que usa a forma aninhada `{ success, data }`. Formatos reais em [api-reference.md](./api-reference.md#formatos-de-resposta).
- IDs são **inteiros sequenciais** gerados pela coleção de contadores (`get_next_sequence`/`get_next_id`), não `ObjectId`. O `_id` do Mongo nunca vaza na resposta — use `utils/serialization.serialize_doc` (ou `normalize_*` do model, que também remove campos sensíveis).
- Schema e índices são garantidos em código via `ensure_*()`, executados no `create_app()`. **Não** crie índices manualmente no banco — adicione ao model.
- `strict_slashes` está desligado globalmente; não dependa de barra final.

## Autenticação

- Há **um único esquema**: JWT via `Authorization: Bearer`. Todos os recursos protegidos usam os decorators de `services/jwt_service.py` — `@jwt_required`, `@jwt_optional`, `@admin_required`, `@owner_or_admin_required('<param>')` —, incluindo usuários, escrita de produtos e categorias e, agora, carrinho, pedidos e favoritos. Não invente esquema próprio por recurso (o antigo `X-User-Id` de favoritos foi removido por ser falsificável).
- A identidade do usuário autenticado vem sempre de **`g.user_id`** (int, derivado da claim `sub`) — nunca de parâmetro de URL, corpo da requisição ou header customizado. O banco guarda `id` como int em users/carts/orders/favorites.
- Toda função de controller que acessa o banco usa o decorator **`@require_db`** (`app/utils/db.py`), que padroniza o 503 (no envelope) quando `current_app.db is None`. Não reimplemente a guarda `if db is None` à mão.
- Nunca logue tokens nem senhas. `JWT_SECRET_KEY` e credenciais ficam em `.env` (nunca commitados).

## Testes

| App | Framework | Local |
|-----|-----------|-------|
| Backend | pytest | `backend/tests/test_*.py` |
| Frontend | Vitest + Testing Library | `*.test.js` ao lado do código |
| Mobile | Jest (configurado, **sem suítes hoje** — [MB-07](./alinhamento-e-debitos.md#mb-07)) | conforme `jest.config.js` |

- Nomeie arquivos de teste como `test_*.py` (backend, exigido pelo `pytest.ini`) ou `*.test.js`/`*.test.ts` (front/mobile).
- Ao corrigir um bug, adicione um teste que o reproduza antes de fechar.
- Rode os testes do app afetado antes de abrir PR.

## Git

- **Branch:** trabalhe em uma branch a partir de `main`; não commite direto na `main`.
- **Commits:** o histórico recente adota *Conventional Commits* (`feat:`, `fix:`, `docs:`, `chore:`...). Mensagem no imperativo e objetiva. Prefira commits pequenos e temáticos.
- **PRs:** descreva o que muda e por quê; referencie a issue quando houver. Inclua passos de teste quando o comportamento muda.

## Variáveis de ambiente e segredos

- Cada app tem seu `.env` (ver [setup-e-deploy.md](./setup-e-deploy.md)); use os `.env.example` como base.
- Prefixos importam: frontend usa `VITE_*`, mobile usa `EXPO_PUBLIC_*` (sem o prefixo a variável não é embarcada no bundle).
- `network-config.json` é gerado por `npm run dev`, **não é versionado** e é apenas um override opcional — cada app detecta o endereço de rede sozinho.

## Estilo de código

- Backend: siga o estilo dos módulos existentes (funções claras, type hints onde já há, mensagens de log com contexto). 
- Frontend/Mobile: rode o linter antes do PR — `npm run lint` em cada app. O mobile é TypeScript; tipe props e retornos de hooks.

## Convenções de documentação

Princípios que mantêm `docs/` fiel ao código (a estrutura da documentação está no [README de docs/](./README.md)):

1. **Realidade > intenção.** Documenta-se o comportamento observável no código, mesmo quando indesejado. O estado ideal só aparece como débito registrado em [alinhamento-e-debitos.md](./alinhamento-e-debitos.md).
2. **Toda afirmação tem fonte.** Cada documento abre com uma linha `> Fonte: <arquivos>`; afirmação não rastreável a um arquivo do repositório não entra. Exemplos de resposta de API devem ser rastreáveis a um `jsonify(...)` real no controller citado — proibido exemplo idealizado.
3. **Cada fato tem casa única.** Endpoints → `docs/api/` (um arquivo por blueprint, mapeamento 1:1 com `app/routes/`); env vars → [setup-e-deploy.md](./setup-e-deploy.md); divergências/débitos → [alinhamento-e-debitos.md](./alinhamento-e-debitos.md); princípios → este documento. Os demais docs **linkam**, nunca copiam.
4. **Débito não se apaga — se resolve.** Item resolvido migra para a seção "Resolvidos" do doc de débitos, com data e hash do commit.
5. **Mudou o contrato, muda a doc no mesmo PR.** Alterou rota, decorator ou shape de resposta → o PR toca o `docs/api/*.md` correspondente (e a matriz de alinhamento, se afetar os clientes).
6. **Todo doc novo entra no índice** (`docs/README.md`) no mesmo commit que o cria.
7. **Idioma:** prosa em pt-BR; identificadores de código (rotas, campos, nomes de arquivo) permanecem exatamente como estão no código.
8. **`CLAUDE.md` ≠ `docs/`.** O `CLAUDE.md` é o guia operacional do agente de código; `docs/` é a documentação normativa para humanos. Sobreposição (comandos, arquitetura) se resolve com link, não com cópia.
9. **Documentos históricos não vivem em `docs/`.** Relatórios de trabalho concluído (reviews, planos de fase) são removidos após migrar o que ainda é vivo para o doc de débitos — o histórico fica no git.
