# Convenções

Padrões para manter consistência ao evoluir o projeto. O objetivo é que código novo "se pareça" com o código existente.

## Idioma

- **Domínio em português:** entidades, campos, rotas de pasta e mensagens ao usuário usam PT-BR (`titulo`, `preco`, `Carrinho`, `Favoritos`). Mantenha esse padrão — não traduza campos do MongoDB para inglês.
- **Termos técnicos e identificadores de framework** ficam na forma original (`store`, `controller`, `blueprint`, `useState`).
- Comentários e documentação: português.

## Estrutura de pastas

### Backend — uma responsabilidade por camada
Ao adicionar um recurso novo, crie os arquivos correspondentes em cada camada e **registre o blueprint** na lista `blueprints_to_register` de `app/__init__.py`:

```
app/routes/<recurso>_routes.py        →  blueprint, URLs, decorators de auth
app/controllers/<recurso>_controller.py →  regras de negócio
app/models/<recurso>_model.py          →  acesso ao Mongo + ensure_indexes()
```

Toda validação de entidade vive no model, em funções `validate_*`, `normalize_*` e `prepare_new_*`. Não espalhe regra de negócio pelo controller ou pela rota.

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

- Respostas seguem o envelope `{ "success": bool, "message": str, ... }`; erros de validação trazem `errors: { campo: motivo }`.
- IDs são **inteiros sequenciais** gerados pela coleção de contadores (`get_next_sequence`), não `ObjectId`. O `_id` do Mongo nunca vaza na resposta (`_serialize` o remove).
- Schema e índices são garantidos em código via `ensure_*()`, executados no `create_app()`. **Não** crie índices manualmente no banco — adicione ao model.
- `strict_slashes` está desligado globalmente; não dependa de barra final.

## Autenticação

- **Todos** os recursos protegidos usam **JWT** (`Authorization: Bearer`) — usuários, escrita de produtos e categorias, e agora também carrinho, pedidos e favoritos. Aplique os decorators existentes: `@jwt_required`, `@admin_required`, `@owner_or_admin_required('<param>')`. A identidade do dono vem sempre de **`g.user_id`** (token), nunca de parâmetro de URL ou header.
- Toda função de controller que acessa o banco deve usar o decorator **`@require_db`** (`app/utils/decorators.py`), que padroniza o 503 quando `current_app.db is None`. Não reimplemente a guarda `if db is None` à mão.
- `g.user_id` é **int** (recuperado de `sub`) e é usado direto em todas as coleções (users/carts/orders/favorites), que guardam id int.
- O antigo header `X-User-Id` de favoritos foi **removido** — não use esse esquema; era forjável. Favoritos legados gravados com `user_id` string precisam de migração string→int à parte.
- Nunca logue tokens nem senhas. `JWT_SECRET_KEY` e credenciais ficam em `.env` (nunca commitados).

## Testes

| App | Framework | Local |
|-----|-----------|-------|
| Backend | pytest | `backend/tests/test_*.py` |
| Frontend | Vitest + Testing Library | `*.test.js` ao lado do código |
| Mobile | Jest + Testing Library RN | conforme `jest.config.js` |

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
- `network-config.json` é gerado por `npm run dev` e **não é versionado**.

## Estilo de código

- Backend: siga o estilo dos módulos existentes (funções claras, type hints onde já há, mensagens de log com contexto). 
- Frontend/Mobile: rode o linter antes do PR — `npm run lint` em cada app. O mobile é TypeScript; tipe props e retornos de hooks.
