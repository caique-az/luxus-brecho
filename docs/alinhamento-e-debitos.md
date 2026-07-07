# Alinhamento e débitos conhecidos

> **Documento vivo.** Toda divergência conhecida — entre apps, entre app e contrato da API, ou entre código e documentação — vive **somente aqui**. Os demais documentos linkam para os IDs desta página, nunca descrevem divergências por conta própria.

## Como usar este documento

- Cada débito tem um **ID estável** (`BE-xx` backend, `FE-xx` frontend web, `MB-xx` mobile, `DOC-xx` documentação/READMEs), o(s) **arquivo(s)-fonte** e o **impacto observável**.
- Débito resolvido **não é apagado**: move para a seção [Resolvidos](#resolvidos) com data e hash do commit.
- Ao alterar um contrato (rota, decorator, shape de resposta), atualize a [matriz de alinhamento](#matriz-de-alinhamento) e os débitos afetados no mesmo PR.

## Matriz de alinhamento

Estado de cada tema em relação ao **contrato do backend** (fonte de verdade). ✅ alinhado · ⚠️ resíduo (funciona, mas carrega legado) · ❌ quebrado contra o backend atual.

| Tema | Backend (contrato) | Web (frontend/) | Mobile (mobile/) |
|------|--------------------|-----------------|------------------|
| Autenticação | JWT Bearer HS256, access 24h / refresh 30d | ✅ interceptor axios injeta Bearer + refresh automático em 401 | ❌ não implementa JWT ([MB-01](#mb-01)) |
| Favoritos | todas as rotas `@jwt_required` | ⚠️ Bearer vai junto, mas ainda envia `X-User-Id` legado ([FE-01](#fe-01)) | ❌ só `X-User-Id` ([MB-02](#mb-02)) |
| Carrinho (peça única) | sem `quantity`; rota `PUT /cart/<id>/update` removida; posse obrigatória | ✅ store sem `quantity` · ⚠️ resíduo no payload do Checkout ([FE-03](#fe-03)) | ❌ modelo ainda tem `quantity` ([MB-04](#mb-04)) |
| Pedidos / Checkout | posse ou admin em todas as rotas | ❌ Checkout usa `fetch` cru sem Bearer ([FE-03](#fe-03)) | ❌ tela de checkout órfã ([MB-05](#mb-05)) |
| Exclusão de conta | `@jwt_required`; alvo = `g.user_id` do token | ❌ envia `user_id` no corpo, sem Authorization ([FE-02](#fe-02)) | ❌ idem ([MB-03](#mb-03)) |

## Débitos do backend

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="be-01"></a>BE-01 | **Envelope `{success}` não padronizado** (padronização deferida na Fase 6). Coexistem três formatos: maioria responde `{message: ...}`; `jwt_service.py` e `images_controller.py` respondem `{'error': ...}`; só health e os error handlers globais (404/500/405/413) respondem `{success: ...}`. Superfície estimada: ~240 `jsonify` em 9 arquivos. Recomendação registrada: criar helpers `ok()/err()` em `utils/` e migrar incrementalmente (nunca num sweep único — risco de acoplamento com parsing do web/mobile). | `backend/app/services/jwt_service.py`, `backend/app/controllers/images_controller.py`, `backend/app/__init__.py` | Um 401 de auth retorna `{"error"}`, enquanto um 404 de produto retorna `{"message"}` — clientes precisam tratar os dois | 2026-07-01 |
| <a id="be-02"></a>BE-02 | **Código morto**: `health_controller.check_health` (a rota de health é inline em `health_routes.py`); `categories_controller.deactivate_category` sem rota registrada; import de `jwt_optional` sem uso em `products_routes.py`. | `backend/app/controllers/health_controller.py`, `backend/app/controllers/categories_controller.py`, `backend/app/routes/products_routes.py` | Correções aplicadas nesses trechos nunca entram em produção | 2026-07-07 |
| <a id="be-03"></a>BE-03 | **`.env.example` incompleto**: faltam `SUPABASE_SERVICE_ROLE_EMAIL`/`SUPABASE_SERVICE_ROLE_KEY` (retry de RLS no storage), `PRODUCTION_URL`/`APP_URL` (base de links de e-mail), tunings `MONGO_*`, `SECRET_KEY`, `MAX_CONTENT_LENGTH`, `FLASK_HOST`/`FLASK_PORT`. A tabela canônica está em [setup-e-deploy.md](./setup-e-deploy.md). | `backend/.env.example` | Deploy configurado só pelo example perde funcionalidades silenciosamente | 2026-07-07 |
| <a id="be-04"></a>BE-04 | **Não há `config.py`**: env vars são lidas inline, espalhadas por `app/__init__.py`, `services/*` e `models/user_model.py`. | `backend/app/` | Difícil enxergar a superfície de configuração; risco de default divergente | 2026-07-07 |
| <a id="be-05"></a>BE-05 | **`JWT_ALGORITHM` do env é ignorada**: o algoritmo é HS256 hardcoded em `jwt_service.py`, embora a var exista no `.env.example`. | `backend/app/services/jwt_service.py` | Definir `JWT_ALGORITHM` no `.env` não tem efeito nenhum | 2026-07-07 |
| <a id="be-06"></a>BE-06 | **Testes rodam contra mock de Mongo em memória** (`conftest.py`): validators JSON Schema, índices únicos e transações reais não são exercitados pela suíte (~185 testes). | `backend/tests/conftest.py` | Regressões em validator/índice só aparecem em runtime | 2026-07-07 |
| <a id="be-07"></a>BE-07 | **`ensure_categories_collection` dropa e recria todos os índices** (exceto `_id_`) a cada boot. | `backend/app/models/category_model.py` | Janela sem índice em todo startup; custo desnecessário em produção | 2026-07-07 |
| <a id="be-08"></a>BE-08 | **Unificação parcial de helpers** (pendência da Fase 6): `parse_pagination` foi aplicado só em `list_users` — as outras ~5 leituras de paginação seguem inline (com clamp correto); `get_next_id`/`get_next_sequence` seguem em 4 cópias contra a coleção `counters`. | `backend/app/utils/pagination.py`, `backend/app/models/*` | Duplicação; mudanças de paginação/geração de ID exigem tocar vários pontos | 2026-07-01 |
| <a id="be-09"></a>BE-09 | **Eficiência** (pendência da Fase 6): `create_product_with_image` faz upload duplo ao Supabase (sobe com `temp_id` e re-sobe com o id real); envio de e-mail SMTP é síncrono no caminho da requisição (signup/confirmação/reset). | `backend/app/routes/products_routes.py`, `backend/app/services/email_service.py` | Criação de produto com imagem paga 2 uploads; latência de e-mail entra no tempo de resposta | 2026-07-01 |

## Débitos do frontend web

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="fe-01"></a>FE-01 | **Header `X-User-Id` legado em favoritos**: `favoritesService` ainda monta `X-User-Id` manualmente em cada chamada. Como as chamadas passam pela instância axios, o Bearer vai junto (interceptor) e o backend ignora o header extra. | `frontend/src/services/favorites.js:22-31` (aplicado nas linhas 41, 69, 95, 118, 135) | Redundante e enganoso — funciona, mas sugere um esquema de auth que não existe mais | 2026-07-07 |
| <a id="fe-02"></a>FE-02 | **Exclusão de conta quebrada**: `requestAccountDeletion`/`confirmAccountDeletion` usam `fetch` cru, sem `Authorization`, enviando `user_id` no corpo. O backend exige `@jwt_required` e lê o alvo de `g.user_id`. | `frontend/src/services/auth.js:304-353`; telas `ExcluirConta/index.jsx`, `ExcluirContaCodigo/index.jsx` | O fluxo de exclusão de conta no web retorna 401 — está quebrado | 2026-07-07 |
| <a id="fe-03"></a>FE-03 | **Checkout com `fetch` cru e resíduo de `quantity`**: `POST /orders/user/<id>` e `GET /users/<id>` são feitos sem Bearer (rotas exigem posse → 401), e o payload do pedido monta `quantity: item.quantity || 1` (o store não tem `quantity`; o backend não usa o campo). | `frontend/src/pages/Checkout/index.jsx:58,135,141-148` | Finalizar compra no web falha com 401; o campo `quantity` enviado é ruído | 2026-07-07 |

## Débitos do mobile

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="mb-01"></a>MB-01 | **Não há JWT no app**: o login só grava a flag `'authenticated'` e `user_data` no AsyncStorage; não existe nenhuma ocorrência de `Authorization`/`Bearer` no código do mobile; não há refresh nem expiração. | `mobile/services/auth.ts` | Toda rota protegida do backend responde 401 para o app | 2026-07-07 |
| <a id="mb-02"></a>MB-02 | **Favoritos via `X-User-Id`**: `fetchWithUserId` injeta o header lido do AsyncStorage; o backend removeu esse esquema (favoritos são `@jwt_required`). | `mobile/services/favorites.ts:27-49` | Favoritos no app estão quebrados (401) | 2026-07-07 |
| <a id="mb-03"></a>MB-03 | **Exclusão de conta com `user_id` no corpo, sem token**: mesmo padrão legado do FE-02. | `mobile/services/auth.ts:239-273`; tela `app/settings/delete.tsx` | Exclusão de conta no app está quebrada (401) | 2026-07-07 |
| <a id="mb-04"></a>MB-04 | **Carrinho ainda modela `quantity`**: `CartItem.quantity`, `getSubtotal` multiplica por quantidade, `updateQuantity` existe e o sync envia `{product_id, quantity}`. O backend removeu `quantity` (peça única) e a rota `/update`. | `mobile/store/cartStore.ts` (interface na linha 13; subtotal :46; updateQuantity :131-151; sync :192-201) | Modelo divergente da regra de domínio; sync carrega campo morto (e exige JWT que o app não tem) | 2026-07-07 |
| <a id="mb-05"></a>MB-05 | **`checkout.tsx` órfão**: o botão "Finalizar Compra" da aba carrinho só exibe um `Alert` e limpa o carrinho — não navega para a tela de checkout, que fica inalcançável no fluxo normal. | `mobile/app/(tabs)/cart.tsx:305-321`, `mobile/app/checkout.tsx` | Não existe fluxo de compra funcional no app | 2026-07-07 |
| <a id="mb-06"></a>MB-06 | **`getApiUrl()` duplicada**: existe em `constants/config.ts` e em `utils/networkUtils.ts`; a efetivamente importada por services/stores/telas é a de `networkUtils.ts`. | `mobile/constants/config.ts:100-110`, `mobile/utils/networkUtils.ts:7-15` | Alterar a versão errada não tem efeito | 2026-07-07 |
| <a id="mb-07"></a>MB-07 | **Sem testes apesar da infraestrutura**: `jest.config.js` existe, mas não há nenhuma suíte; `mobile/tests/` contém apenas `requirements.txt` e `robot/resources/config.robot`. | `mobile/jest.config.js`, `mobile/tests/` | `npm test` não exercita nada; o README prometia cobertura ([DOC-03](#doc-03)) | 2026-07-07 |

## Débitos de documentação (READMEs)

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="doc-01"></a>DOC-01 | **README da raiz** diz que `npm run dev:full` sobe backend + frontend; `start-dev.js` sobe backend + **mobile**. As afirmações de "JWT" e "peça única sem quantity" valem só para o web. | `README.md`, `start-dev.js` | Comando documentado não faz o que promete | 2026-07-07 |
| <a id="doc-02"></a>DOC-02 | **`backend/README.md`** documenta 5 de ~50 rotas, omite `ADMIN_EMAIL`/`ADMIN_PASSWORD` (sem elas não há seed de admin), omite `@owner_or_admin_required`/`@jwt_optional` e sugere `JWT_ALGORITHM` configurável (é ignorada — [BE-05](#be-05)). | `backend/README.md` | Setup guiado só pelo README resulta em banco sem admin | 2026-07-07 |
| <a id="doc-03"></a>DOC-03 | **`mobile/README.md`** afirma Expo 54 (o `package.json` tem Expo ^49), autenticação JWT (não há — [MB-01](#mb-01)) e testes Jest (não há — [MB-07](#mb-07)). | `mobile/README.md`, `mobile/package.json` | Expectativas falsas sobre o estado do app | 2026-07-07 |

## Resolvidos

| ID | Débito | Resolvido em | Commit |
|----|--------|--------------|--------|
| — | *(nenhum ainda)* | | |

---

> **Origem histórica:** a maior parte dos débitos do backend foi identificada no code review de 2026-07-01 e tratada em 6 fases (Fases 1–5 concluídas; Fase 6 parcial — BE-01, BE-08 e BE-09 são exatamente as pendências que sobraram). Os relatórios de trabalho originais foram removidos do repositório após a migração do status para este documento; eles permanecem acessíveis no histórico do git (`docs/code-review-backend.md` e `docs/plano-desenvolvimento-backend.md`, até o commit que os removeu).
