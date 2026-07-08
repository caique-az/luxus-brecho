# Usuários e autenticação — `/api/users`

> Fonte: `backend/app/routes/users_routes.py` · `backend/app/controllers/users_controller.py` · `backend/app/models/user_model.py`
> Contrato geral (auth, formatos, erros): [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md)

## Resumo

| Método | Rota | Auth | Rate limit | Descrição |
|--------|------|------|------------|-----------|
| GET | `/api/users/` | `@admin_required` | — | Lista usuários (paginação + filtros) |
| GET | `/api/users/<int:id>` | `@owner_or_admin_required('id')` | — | Detalhe de um usuário |
| POST | `/api/users/` | pública | — | Registro — **sempre cria Cliente** |
| POST | `/api/users/admin` | `@admin_required` | — | Cria um administrador |
| PUT | `/api/users/<int:id>` | `@owner_or_admin_required('id')` | — | Atualiza dados |
| DELETE | `/api/users/<int:id>` | `@admin_required` | — | Desativa usuário (soft delete) |
| POST | `/api/users/auth` | pública | 10/min; 50/h | Login → tokens |
| PUT | `/api/users/<int:id>/change-password` | `@owner_or_admin_required('id')` | — | Altera senha |
| POST | `/api/users/refresh-token` | pública (valida refresh) | — | Renova o par de tokens |
| POST | `/api/users/forgot-password` | pública | 5/h | Inicia recuperação de senha |
| POST | `/api/users/reset-password` | pública | 10/h | Redefine senha via token |
| GET | `/api/users/confirm-email/<string:token>` | pública | — | Confirma e-mail de cadastro |
| POST | `/api/users/resend-confirmation` | pública | 3/h | Reenvia e-mail de confirmação |
| GET | `/api/users/types` | pública | — | Tipos de usuário |
| GET | `/api/users/summary` | pública | — | Contagem de usuários por tipo |
| POST | `/api/users/request-deletion` | `@jwt_required` | 5/h | Solicita exclusão da **própria** conta |
| POST | `/api/users/confirm-deletion` | `@jwt_required` | 10/h | Confirma exclusão com código de 6 dígitos |

Os rate limits específicos só se aplicam quando `flask-limiter` está instalado (além do default global de 200/dia e 50/h).

## Registro e criação de admin

**`POST /api/users/`** — registro público. Body:

```json
{ "nome": "Maria", "email": "maria@ex.com", "senha": "senha123", "telefone": "...", "endereco": { ... } }
```

- O campo `tipo` do payload é **ignorado**: o registro público sempre cria `Cliente` (`_create_user_with_tipo` impõe o tipo pela rota — bloqueio de auto-registro de admin).
- Regras: `nome` 2–100 chars; `email` válido e único (409 se em uso); senha com mínimo 6 chars, ≥1 letra e ≥1 número; `endereco` (opcional) exige `rua`, `numero`, `bairro`, `cidade`, `estado` (2 letras), `cep` (8 dígitos).
- Clientes nascem **inativos e não confirmados**: recebem e-mail com link de confirmação (token expira em 24h). Resposta 201:

```json
{ "message": "Usuário criado com sucesso. Verifique seu email para confirmar a conta.", "user": { ... }, "email_confirmation_required": true }
```

**`POST /api/users/admin`** — mesmo body, mas cria `Administrador`; só um admin autenticado pode chamar. Admins nascem **ativos e confirmados** (sem fluxo de confirmação de e-mail).

> O **primeiro** admin não é criado por endpoint: é semeado no boot a partir de `ADMIN_EMAIL`/`ADMIN_PASSWORD`/`ADMIN_NAME` (`create_default_admin` em `user_model.py`). Sem essas env vars, não há seed — ver [../setup-e-deploy.md](../setup-e-deploy.md).

## Login, refresh e senha

**`POST /api/users/auth`** — body `{"email", "senha"}`. Erros: 401 `{"message": "Credenciais inválidas"}`; 403 com `email_not_confirmed: true` se o e-mail não foi confirmado; 403 se a conta está desativada. Sucesso 200:

```json
{
  "message": "Autenticação realizada com sucesso",
  "user": { "id": 5, "nome": "...", "email": "...", "tipo": "Cliente", "ativo": true, ... },
  "access_token": "...", "refresh_token": "...",
  "token_type": "Bearer", "expires_in": 86400
}
```

**`POST /api/users/refresh-token`** — body `{"refresh_token"}`. Valida o refresh, relê o usuário no banco (usuário inexistente/desativado → 401 `{"message": ...}`) e responde um **novo par** de tokens: `{"access_token", "refresh_token", "token_type": "Bearer", "expires_in": 86400}`.

**`PUT /api/users/<id>/change-password`** — body `{"senha_atual", "senha_nova"}`. 400 se a senha atual não confere ou a nova viola a política.

**`POST /api/users/forgot-password`** — body `{"email"}`. Sempre responde 200 com mensagem genérica (não revela se o e-mail existe). Quando existe, grava `reset_token` (expira em 1h) e envia e-mail com link `FRONTEND_URL/redefinir-senha/<token>`.

**`POST /api/users/reset-password`** — body `{"token", "nova_senha"}`. 400 para token inválido/expirado ou senha fraca; 200 `{"message": "Senha redefinida com sucesso"}`.

## Confirmação de e-mail

**`GET /api/users/confirm-email/<token>`** — confirma o e-mail, **ativa a conta** e limpa o token. 404 para token inválido/já usado; 410 para token expirado. Dispara e-mail de boas-vindas.

**`POST /api/users/resend-confirmation`** — body `{"email"}`. Gera novo token e reenvia. Se o e-mail não existe, responde 200 genérico; se já confirmado, 400.

## Exclusão de conta (2 passos, autenticada)

Ambas exigem `@jwt_required`; **o alvo é sempre `g.user_id`** (o id do token) — o `user_id` do corpo é ignorado. Web e mobile já enviam o `Authorization: Bearer` nesses fluxos.

1. **`POST /api/users/request-deletion`** — sem body relevante. Gera código de **6 dígitos** (expira em 30 min, contador de tentativas zerado) e o envia por e-mail. 200: `{"message": "Código de verificação enviado para seu email", "email_sent": true}`.
2. **`POST /api/users/confirm-deletion`** — body `{"code": "123456"}`. Comparação em tempo constante (`secrets.compare_digest`); código errado incrementa `deletion_attempts` (400) e a **5ª falha invalida o código** (429); código expirado → 410. Sucesso: `delete_one` **permanente** — 200 `{"message": "Conta excluída com sucesso", "deleted": true}`.

## Listagem, consulta e gestão

**`GET /api/users/`** (admin) — query: `page`/`page_size` (via `parse_pagination`, clamp 1–100), `tipo`, `ativo` (`true`/`false`), `search` (regex case-insensitive em `nome`/`email`, termo escapado com `re.escape`). Resposta `{"items": [...], "pagination": {...}}`.

**`GET /api/users/<id>`** — o documento do usuário direto (sem envelope), passado por `normalize_user` (remove `_id`, `senha_hash`, tokens; datas em ISO).

**`PUT /api/users/<id>`** — merge parcial dos campos `nome`, `email`, `tipo`, `ativo`, `telefone`, `endereco`, `senha`. 409 se o novo e-mail já está em uso. Resposta `{"message": "Usuário atualizado com sucesso", "user": {...}}`.

**`DELETE /api/users/<id>`** (admin) — **soft delete** (`ativo: false`). Recusa desativar o último administrador ativo (400).

**`GET /api/users/types`** — `{"types": ["Administrador", "Cliente"], "message": ...}`.

**`GET /api/users/summary`** — `{"summary": {"Administrador": 1, "Cliente": 42}, "total": 43, "message": ...}`. **Nota:** é pública — expõe contagem de usuários sem auth.

## Notas de implementação

- Coleção `users` com JSON Schema validator (required: `id`, `nome`, `email`, `senha_hash`, `tipo`, `ativo`). Índices: únicos em `id` e `email`; simples em `tipo` e `ativo`; TEXT em `nome`; **esparsos** em `token_confirmacao` e `reset_token` (lookups de confirmação/reset sem full scan).
- Senhas com bcrypt (`hash_password`/`verify_password`).
- E-mails (confirmação, boas-vindas, reset, código de exclusão) são enviados de forma **síncrona** no caminho da requisição ([BE-09](../alinhamento-e-debitos.md#be-09)).
