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
| Autenticação | JWT Bearer HS256, access 24h / refresh 30d | ✅ interceptor axios injeta Bearer + refresh automático em 401 | ✅ armazena tokens, injeta Bearer e renova em 401 |
| Favoritos | todas as rotas `@jwt_required` | ⚠️ Bearer vai junto, mas ainda envia `X-User-Id` legado ([FE-01](#fe-01)) | ⚠️ Bearer vai junto, mas ainda envia `X-User-Id` legado ([MB-02](#mb-02)) |
| Carrinho (peça única) | sem `quantity`; rota `PUT /cart/<id>/update` removida; posse obrigatória | ✅ store sem `quantity` · ⚠️ resíduo no payload do Checkout ([FE-03](#fe-03)) | ❌ modelo ainda tem `quantity` ([MB-04](#mb-04)) |
| Pedidos / Checkout | posse ou admin em todas as rotas | ✅ Checkout e Pedidos usam a instância axios (Bearer) · ⚠️ resíduo `quantity` no payload ([FE-03](#fe-03)) | ❌ checkout fora do fluxo principal ([MB-05](#mb-05)) |
| Exclusão de conta | `@jwt_required`; alvo = `g.user_id` do token | ✅ envia Authorization Bearer | ✅ envia Authorization Bearer |

## Débitos do backend

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="be-02"></a>BE-02 | **Código morto**: `health_controller.check_health` (a rota de health é inline em `health_routes.py`); `categories_controller.deactivate_category` sem rota registrada; import de `jwt_optional` sem uso em `products_routes.py`. | `backend/app/controllers/health_controller.py`, `backend/app/controllers/categories_controller.py`, `backend/app/routes/products_routes.py` | Correções aplicadas nesses trechos nunca entram em produção | 2026-07-07 |
| <a id="be-03"></a>BE-03 | **`.env.example` incompleto**: faltam `SUPABASE_SERVICE_ROLE_EMAIL`/`SUPABASE_SERVICE_ROLE_KEY` (retry de RLS no storage), `PRODUCTION_URL`/`APP_URL` (base de links de e-mail), tunings `MONGO_*`, `SECRET_KEY`, `MAX_CONTENT_LENGTH`, `FLASK_HOST`/`FLASK_PORT`. A tabela canônica está em [setup-e-deploy.md](./setup-e-deploy.md). | `backend/.env.example` | Deploy configurado só pelo example perde funcionalidades silenciosamente | 2026-07-07 |
| <a id="be-04"></a>BE-04 | **Não há `config.py`**: env vars são lidas inline, espalhadas por `app/__init__.py`, `services/*` e `models/user_model.py`. | `backend/app/` | Difícil enxergar a superfície de configuração; risco de default divergente | 2026-07-07 |
| <a id="be-05"></a>BE-05 | **`JWT_ALGORITHM` do env é ignorada**: o algoritmo é HS256 hardcoded em `jwt_service.py`, embora a var exista no `.env.example`. | `backend/app/services/jwt_service.py` | Definir `JWT_ALGORITHM` no `.env` não tem efeito nenhum | 2026-07-07 |
| <a id="be-06"></a>BE-06 | **Testes rodam contra mock de Mongo em memória** (`conftest.py`): validators JSON Schema, índices únicos e transações reais não são exercitados pela suíte (~185 testes). | `backend/tests/conftest.py` | Regressões em validator/índice só aparecem em runtime | 2026-07-07 |
| <a id="be-07"></a>BE-07 | **`ensure_categories_collection` dropa e recria todos os índices** (exceto `_id_`) a cada boot. | `backend/app/models/category_model.py` | Janela sem índice em todo startup; custo desnecessário em produção | 2026-07-07 |
| <a id="be-08"></a>BE-08 | **Unificação parcial de helpers** (pendência da Fase 6): `parse_pagination` foi aplicado só em `list_users` — as outras ~4 leituras de paginação seguem inline (com clamp correto); `get_next_id`/`get_next_sequence` seguem em 4 cópias contra a coleção `counters`. | `backend/app/utils/pagination.py`, `backend/app/models/*` | Duplicação; mudanças de paginação/geração de ID exigem tocar vários pontos | 2026-07-01 |
| <a id="be-09"></a>BE-09 | **Eficiência** (pendência da Fase 6): `create_product_with_image` faz upload duplo ao Supabase (sobe com `temp_id` e re-sobe com o id real); envio de e-mail SMTP é síncrono no caminho da requisição (signup/confirmação/reset). | `backend/app/routes/products_routes.py`, `backend/app/services/email_service.py` | Criação de produto com imagem paga 2 uploads; latência de e-mail entra no tempo de resposta | 2026-07-01 |

## Débitos do frontend web

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="fe-01"></a>FE-01 | **Header `X-User-Id` legado em favoritos**: `favoritesService` ainda monta `X-User-Id` manualmente em cada chamada. Como as chamadas passam pela instância axios, o Bearer vai junto (interceptor) e o backend ignora o header extra. | `frontend/src/services/favorites.js:22-31` (aplicado nas linhas 41, 69, 95, 118, 137) | Redundante e enganoso — funciona, mas sugere um esquema de auth que não existe mais | 2026-07-07 |
| <a id="fe-03"></a>FE-03 | **Resíduo de `quantity` no payload do Checkout**: o Checkout já usa a instância axios (`api.get`/`api.post`, com Bearer), mas ainda monta `quantity: item.quantity || 1` no item do pedido — o store é peça única (sem `quantity`) e o backend ignora o campo. | `frontend/src/pages/Checkout/index.jsx:133` | O campo `quantity` enviado é ruído (sem efeito funcional) | 2026-07-07 |

## Débitos do mobile

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="mb-02"></a>MB-02 | **Header `X-User-Id` legado em favoritos**: `fetchWithUserId` já injeta o `Authorization: Bearer` (via `authService.getAuthHeaders()`), mas ainda anexa o `X-User-Id` lido do AsyncStorage. O backend ignora o header extra. | `mobile/services/favorites.ts:38-41` | Redundante e enganoso — funciona, mas sugere um esquema de auth que não existe mais | 2026-07-07 |
| <a id="mb-04"></a>MB-04 | **Carrinho ainda modela `quantity`**: `CartItem.quantity`, `getSubtotal` multiplica por quantidade, `updateQuantity` existe e o sync envia `{product_id, quantity}`. O backend removeu `quantity` (peça única) e a rota `/update`. | `mobile/store/cartStore.ts` (interface na linha 13; subtotal :46; updateQuantity :131-151; sync :192-201) | Modelo divergente da regra de domínio; sync carrega campo morto (e exige JWT que o app não tem) | 2026-07-07 |
| <a id="mb-05"></a>MB-05 | **Checkout fora do fluxo (loop morto)**: o botão "Finalizar Compra" da aba carrinho só exibe um `Alert` e limpa o carrinho — não navega para checkout. A tela `checkout.tsx` só é alcançada por `orders.tsx:373`, que por sua vez só é alcançada de volta por `checkout.tsx:144` — um par isolado, sem entrada pelo fluxo principal. | `mobile/app/(tabs)/cart.tsx:305-321`, `mobile/app/orders.tsx:372-378`, `mobile/app/checkout.tsx:144` | Não existe fluxo de compra funcional no app | 2026-07-07 |
| <a id="mb-06"></a>MB-06 | **`getApiUrl()` duplicada**: existe em `constants/config.ts` e em `utils/networkUtils.ts`; a efetivamente importada por services/stores/telas é a de `networkUtils.ts`. | `mobile/constants/config.ts:100-110`, `mobile/utils/networkUtils.ts:7-15` | Alterar a versão errada não tem efeito | 2026-07-07 |
| <a id="mb-07"></a>MB-07 | **Sem testes apesar da infraestrutura**: `jest.config.js` existe, mas não há nenhuma suíte; `mobile/tests/` contém apenas `requirements.txt` e `robot/resources/config.robot`. | `mobile/jest.config.js`, `mobile/tests/` | `npm test` não exercita nada; o README prometia cobertura ([DOC-03](#doc-03)) | 2026-07-07 |
| <a id="mb-09"></a>MB-09 | **Keystore de release vazado em logs públicos (CI)**: o job "Build Android APK" usava `eas build --local`, que baixa o keystore de assinatura para o runner e o imprime em base64 (com `keystorePassword`/`keyPassword`) ao reportar falha do Gradle. Como o repositório é **público**, o keystore de release e as senhas ficaram expostos nos logs de todo run que falhou. **Mitigado**: migração para EAS cloud build (`d6cbb7d`, o keystore não desce mais ao runner) + deleção dos 11 runs falhos que continham os segredos. **Pendente (mantenedor)**: rotacionar o keystore comprometido — o atual deve ser considerado queimado (runbook em [setup-e-deploy](./setup-e-deploy.md#build-e-assinatura-do-mobile-no-ci)). | `.github/workflows/mobile-build.yml` | Qualquer pessoa pôde baixar o keystore de release e assinar APKs se passando pelo app | 2026-07-16 |

## Débitos de documentação (READMEs)

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| — | *(nenhum aberto)* | | | |

## Resolvidos

| ID | Débito | Resolvido em | Commit |
|----|--------|--------------|--------|
| <a id="doc-01"></a>DOC-01 | README da raiz dizia que `npm run dev:full` sobe backend + frontend (é backend + **mobile**) e generalizava "JWT"/"peça única" para os dois clientes | 2026-07-07 | `1ce9f56` |
| <a id="doc-02"></a>DOC-02 | `backend/README.md` documentava 5 de ~50 rotas, omitia `ADMIN_*` (seed de admin) e sugeria `JWT_ALGORITHM` configurável | 2026-07-07 | `1ce9f56` |
| <a id="doc-03"></a>DOC-03 | `mobile/README.md` afirmava Expo 54, autenticação JWT e testes Jest — nada disso existia no app | 2026-07-07 | `1ce9f56` |
| <a id="be-01"></a>BE-01 | **Envelope `{success, ...}` padronizado**: helpers `ok()`/`err()` em `utils/responses.py` usados por todos os controllers, rotas e errorhandlers; a chave `error` (auth/imagens) foi unificada em `message`. Contrato travado em `tests/test_envelope.py`. | 2026-07-07 | `1152751` |
| <a id="mb-01"></a>MB-01 | **Mobile passou a usar JWT real**: armazena access/refresh no AsyncStorage, injeta `Authorization: Bearer` (`getAuthHeaders`) e renova em 401. | 2026-07-07 | `e347454` |
| <a id="fe-02"></a>FE-02 | **Exclusão de conta no web** passou a enviar `Authorization: Bearer` em `requestAccountDeletion`/`confirmAccountDeletion`. | 2026-07-07 | `24372a6` |
| <a id="mb-03"></a>MB-03 | **Exclusão de conta no app** passou a enviar `Authorization: Bearer` (via `getAuthHeaders`). | 2026-07-07 | `24372a6` |
| <a id="mb-08"></a>MB-08 | **Build Android quebrado por `react-native-worklets` órfão**: `react-native-worklets@0.5.1` (exige RN ≥ 0.78) sobrou da atualização para o SDK54 (`c979ccc`) depois que `expo`/`react-native`/`reanimated` foram revertidos ao SDK49. O Gradle reprovava em `:react-native-worklets:assertMinimalReactNativeVersionTask` contra RN 0.72.10, deixando todo PR com o check "Build Android APK" vermelho. Removida a dependência direta (não importada em lugar nenhum — o Reanimated 3.x já embute os worklets). | 2026-07-16 | `a8f10e0` |

---

> **Origem histórica:** a maior parte dos débitos do backend foi identificada no code review de 2026-07-01 e tratada em 6 fases (Fases 1–5 concluídas; a Fase 6 fechou o envelope (BE-01) no PR de débitos técnicos, restando BE-08 e BE-09 como pendências). Os relatórios de trabalho originais foram removidos do repositório após a migração do status para este documento; eles permanecem acessíveis no histórico do git (`docs/code-review-backend.md` e `docs/plano-desenvolvimento-backend.md`, até o commit que os removeu).
