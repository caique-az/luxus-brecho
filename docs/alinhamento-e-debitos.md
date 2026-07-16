# Alinhamento e débitos conhecidos

> **Documento vivo.** Toda divergência conhecida — entre apps, entre app e contrato da API, ou entre código e documentação — vive **somente aqui**. Os demais documentos linkam para os IDs desta página, nunca descrevem divergências por conta própria.

## Como usar este documento

- Cada débito tem um **ID estável** (`BE-xx` backend, `FE-xx` frontend web, `MB-xx` mobile, `CI-xx` automação/qualidade, `DOC-xx` documentação/READMEs), o(s) **arquivo(s)-fonte** e o **impacto observável**.
- Débito resolvido **não é apagado**: move para a seção [Resolvidos](#resolvidos) com data e hash do commit.
- Ao alterar um contrato (rota, decorator, shape de resposta), atualize a [matriz de alinhamento](#matriz-de-alinhamento) e os débitos afetados no mesmo PR.

## Matriz de alinhamento

Estado de cada tema em relação ao **contrato do backend** (fonte de verdade). ✅ alinhado · ⚠️ resíduo (funciona, mas carrega legado) · ❌ quebrado contra o backend atual.

| Tema | Backend (contrato) | Web (frontend/) | Mobile (mobile/) |
|------|--------------------|-----------------|------------------|
| Autenticação | JWT Bearer HS256, access 24h / refresh 30d | ✅ interceptor axios injeta Bearer + refresh automático em 401 | ✅ armazena tokens, injeta Bearer e renova em 401 |
| Favoritos | todas as rotas `@jwt_required` | ✅ só Bearer, via interceptor | ✅ só Bearer, via `getAuthHeaders` |
| Carrinho (peça única) | sem `quantity`; rota `PUT /cart/<id>/update` removida; posse obrigatória | ✅ store sem `quantity` | ❌ modelo ainda tem `quantity` ([MB-04](#mb-04)) |
| Pedidos / Checkout | posse ou admin em todas as rotas | ✅ Checkout e Pedidos usam a instância axios (Bearer); payload só com `product_id` | ❌ checkout fora do fluxo principal ([MB-05](#mb-05)) |
| Exclusão de conta | `@jwt_required`; alvo = `g.user_id` do token | ✅ envia Authorization Bearer | ✅ envia Authorization Bearer |
| Configuração por env | — | ✅ `VITE_*` inlinada pelo Vite | ❌ toda `EXPO_PUBLIC_*` cai no fallback ([MB-09](#mb-09)) |

## Débitos do backend

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="be-10"></a>BE-10 | **Categoria pode ser reativada, mas não desativada**: existe `PUT /categories/<id>/activate` (`activate_category`, com rota registrada), e não há contraparte para desativar. O `deactivate_category` existia no controller sem rota nenhuma e foi removido como código morto em [BE-02](#be-02) — o campo `active` do model e o filtro `?active_only=true` da listagem continuam de pé. Decidir: registrar a rota que falta (se o soft-delete é intencional) ou remover `activate_category` e o campo (se não é). Hoje `active` só vira `false` na criação, então o filtro nunca exclui nada na prática. | `backend/app/controllers/categories_controller.py` (`activate_category`), `backend/app/routes/categories_routes.py:24` | API assimétrica: a única forma de tirar uma categoria do ar é o delete permanente | 2026-07-16 |
| <a id="be-06"></a>BE-06 | **Testes rodam contra mock de Mongo em memória** (`conftest.py`): validators JSON Schema, índices únicos e transações reais não são exercitados pela suíte (~185 testes). | `backend/tests/conftest.py` | Regressões em validator/índice só aparecem em runtime | 2026-07-07 |
| <a id="be-09"></a>BE-09 | **E-mail SMTP síncrono no caminho da requisição** (signup/confirmação/reset). A metade do upload duplo foi resolvida (`350f3da`); esta permanece **por decisão**, não por esquecimento: o backend roda em Vercel serverless (`@vercel/python` sobre `index.py`), onde o processo é congelado assim que a resposta HTTP sai. Mandar o envio para uma `threading.Thread` — a correção óbvia — faria a thread ser morta no meio do SMTP e o e-mail de confirmação **não chegar**, trocando ~2s de latência por perda silenciosa de cadastro. Resolver de verdade exige decisão de infra: fila externa (Redis/QStash) ou trocar SMTP por API HTTP (Resend/SendGrid), que responde em ~200ms. | `backend/app/services/email_service.py`, `backend/app/controllers/users_controller.py:176,532,587,633` | Latência do SMTP entra no tempo de resposta do cadastro e do reset de senha | 2026-07-01 |

## Débitos do frontend web

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| — | *(nenhum aberto)* | | | |

## Débitos do mobile

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="mb-04"></a>MB-04 | **Carrinho ainda modela `quantity`**: `CartItem.quantity`, `getSubtotal` multiplica por quantidade, `updateQuantity` existe e o sync envia `{product_id, quantity}`. O backend removeu `quantity` (peça única) e a rota `/update`. | `mobile/store/cartStore.ts` (interface na linha 13; subtotal :46; updateQuantity :131-151; sync :192-201) | Modelo divergente da regra de domínio; sync carrega campo morto (e exige JWT que o app não tem) | 2026-07-07 |
| <a id="mb-05"></a>MB-05 | **Checkout fora do fluxo (loop morto)**: o botão "Finalizar Compra" da aba carrinho só exibe um `Alert` e limpa o carrinho — não navega para checkout. A tela `checkout.tsx` só é alcançada por `orders.tsx:373`, que por sua vez só é alcançada de volta por `checkout.tsx:144` — um par isolado, sem entrada pelo fluxo principal. | `mobile/app/(tabs)/cart.tsx:305-321`, `mobile/app/orders.tsx:372-378`, `mobile/app/checkout.tsx:144` | Não existe fluxo de compra funcional no app | 2026-07-07 |
| <a id="mb-09"></a>MB-09 | **Toda `EXPO_PUBLIC_*` é ignorada no bundle**: os helpers `getEnvValue`/`getEnvBoolean`/`getEnvNumber` acessam `process.env[key]` (dinâmico), mas o Metro do Expo inlina env vars com o regex `/process\.env\.([a-zA-Z0-9_]+)/`, que **só casa com acesso por ponto**. O acesso dinâmico não é substituído e, como `process.env` não existe em runtime no app, as **26** chamadas caem sempre no fallback. Verificado executando o serializer real (`@expo/metro-config/build/serializer/environmentVariableSerializerPlugin`): `process.env.EXPO_PUBLIC_X` → `"valor"`; `process.env[k]` → intacto. Corrigir exige acesso estático literal por variável (a assinatura `getEnvValue(key)` não sobrevive) — e **muda comportamento em produção**, então merece PR próprio e teste em dispositivo. | `mobile/constants/config.ts:22-60` (helpers e os 26 usos) | `EXPO_PUBLIC_PRODUCTION_URL` não tem efeito: em produção o app usa o fallback vindo do `network-config.json` — arquivo **gerado e não versionado**, com o IP da Wi-Fi de quem rodou `npm run dev` por último. O mesmo vale para timeouts, cache e frete. | 2026-07-16 |
| <a id="mb-10"></a>MB-10 | **`npm run lint` nunca rodou e há 90 erros represados**: `eslint.config.js` declarava `@typescript-eslint/prefer-const`, regra inexistente no plugin, o que derrubava o ESLint inteiro (`Could not find "prefer-const" in plugin`). A config foi corrigida (`177b837`) e os erros de `constants/config.ts` tratados, mas o lint do app inteiro acusa **209 problemas (90 erros, 119 warnings)** acumulados — nenhum deles em código tocado por este PR. | `mobile/` (app/, components/, hooks/, store/) | `npm run lint` sai com exit 1; plugar o lint num workflow hoje reprovaria todo PR. Foi essa config quebrada que manteve [MB-09](#mb-09) invisível — a regra `expo/no-dynamic-env-var` existe exatamente para isso. | 2026-07-16 |
| <a id="mb-07"></a>MB-07 | **Sem testes apesar da infraestrutura**: `jest.config.js` existe, mas não há nenhuma suíte; `mobile/tests/` contém apenas `requirements.txt` e `robot/resources/config.robot`. | `mobile/jest.config.js`, `mobile/tests/` | `npm test` não exercita nada; o README prometia cobertura ([DOC-03](#doc-03)) | 2026-07-07 |

## Débitos de CI e ferramentas de qualidade

> Tema comum: as ferramentas existem e **falham em silêncio**. Foi uma config de lint quebrada que manteve [MB-09](#mb-09) invisível por meses — a regra que o pega estava instalada o tempo todo.

| ID | Débito | Fonte | Impacto observável | Registrado em |
|----|--------|-------|--------------------|---------------|
| <a id="ci-01"></a>CI-01 | **Nenhum workflow roda a suíte de testes**: os dois workflows existentes fazem análise de segurança (`security-tests.yml`) e build de APK (`mobile-build.yml`). `pytest` e `vitest` não aparecem em nenhum — verificado por grep em `.github/workflows/`. | `.github/workflows/` | 213 testes de backend e 37 de frontend só protegem quem lembra de rodá-los na própria máquina; um PR pode quebrar a suíte e ficar verde | 2026-07-16 |
| <a id="ci-02"></a>CI-02 | **Build de APK dispara em todo PR**: o gatilho `push` filtra `paths: ['mobile/**']`, mas o `pull_request` não tem filtro nenhum. | `.github/workflows/mobile-build.yml:8-11` | Todo PR — inclusive os que só tocam Python ou documentação — espera ~9 min de build Android e consome minutos de Actions. Observado no PR #21, que só altera backend/docs | 2026-07-16 |
| <a id="ci-03"></a>CI-03 | **Typecheck do mobile nunca roda**: `tsconfig.json` define `"ignoreDeprecations": "6.0"`, valor aceito só no TypeScript 6.x — o projeto usa `typescript@^5.8.3`. O compilador aborta com `error TS5103: Invalid value for '--ignoreDeprecations'` antes de checar qualquer arquivo. A intenção (pelo comentário na linha) era silenciar avisos de `baseUrl`/`moduleResolution`; no 5.x o valor válido é `"5.0"`. | `mobile/tsconfig.json:16` | `npx tsc --noEmit` sai com erro de config, não de tipo: o app é TypeScript mas **nenhum erro de tipo é detectado**, nem localmente nem em CI | 2026-07-16 |
| <a id="ci-04"></a>CI-04 | **`npm run lint` do frontend falha**: 42 problemas (25 erros, 17 warnings) acumulados, incluindo `'process' is not defined` em `vite.config.js` (arquivo de config Node avaliado com as globals do browser). | `frontend/` (`vite.config.js` e outros) | `npm run lint` sai com exit 1; plugar o lint num workflow hoje reprovaria todo PR. Equivalente web do [MB-10](#mb-10) | 2026-07-16 |

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
| <a id="fe-01"></a>FE-01 | **Header `X-User-Id` legado removido do web**: `favoritesService` montava o header à mão; o Bearer já ia pelo interceptor. Removido junto o guard local que lançava `Usuário não autenticado` antes de qualquer rede — ele só existia porque o esquema antigo precisava do `user_id` para montar o header, e nenhum outro service do projeto faz isso. `src/services/favorites.test.js` (8 casos) cobre o contrato, que não tinha teste algum. | 2026-07-16 | `2ea0105` |
| <a id="fe-03"></a>FE-03 | **Payload morto do Checkout removido**: eram **quatro** campos ignorados, não só o `quantity` registrado. O controller usa apenas `product_id` e resolve preço, título e imagem a partir do banco — confiar no preço enviado pelo cliente abriria manipulação de valor, e `preco_unitario` sugeria um contrato inexistente. | 2026-07-16 | `2ea0105` |
| <a id="mb-02"></a>MB-02 | **Header `X-User-Id` legado removido do app**: `fetchWithUserId` anexava o header além do Bearer; renomeado para `fetchAutenticado`, sem o guard local. | 2026-07-16 | `177b837` |
| <a id="mb-06"></a>MB-06 | **`getApiUrl()` duplicada resolvida**: a cópia de `constants/config.ts` não era importada por ninguém — os 9 consumidores usam a de `utils/networkUtils.ts`. Removida a morta. | 2026-07-16 | `177b837` |
| <a id="be-03"></a>BE-03 | **`.env.example` completo**: acrescenta as variáveis que o código lia e o example omitia (tunings `MONGO_*`, `SECRET_KEY`, `MAX_CONTENT_LENGTH`, `FLASK_HOST`/`PORT`/`ENV`, `SUPABASE_SERVICE_ROLE_*`, `PRODUCTION_URL`/`APP_URL`), as opcionais comentadas com o default real. Documenta o que não era óbvio: a precedência das URLs de e-mail, o papel do service role (retry quando a RLS barra o upload) e a diferença entre `SECRET_KEY` (sessão) e `JWT_SECRET_KEY` (tokens). Verificado por diff das duas listas — nenhuma var lida está ausente, nenhuma declarada é ignorada. | 2026-07-16 | `cac9ee9` |
| <a id="be-04"></a>BE-04 | **`app/config.py` criado**: cada env var tem uma função que concentra nome, default e parsing; nenhum módulo lê `os.environ` por conta própria. Funções, não constantes — ler no import quebraria o `monkeypatch.setenv` de `test_phase4_admin_seed`. Corrigiu um efeito real além da organização: os tunings do Mongo faziam `int()` cru, então `MONGO_MAX_POOL_SIZE=abc` estourava dentro do bloco de conexão, que engolia a exceção e deixava o app **subir sem banco** (tudo 503, com a mensagem culpando a rede em vez do typo); agora avisa e usa o default. `JWT_SECRET_KEY` segue lida no import de `jwt_service` de propósito (fail-fast no startup). | 2026-07-16 | `7e751a4` |
| <a id="be-08"></a>BE-08 | **Helpers unificados**: as três leituras de paginação inline (`list_categories`, `get_user_orders`, `get_products_by_category`) passaram a usar `parse_pagination`. Isso corrigiu um **500 não registrado**: elas faziam `int()` cru na query string, então `?page=abc` levantava ValueError — reproduzido em categories, orders e products/category antes da correção. A listagem de products (rota `/`) segue validando por Marshmallow (400), contrato preservado. `user_model.get_next_id` era a última cópia real do contador e passou a delegar para `utils.counters.next_sequence`. Travado por `tests/test_pagination.py`. | 2026-07-16 | `cae22c6`, `d7e1998` |
| <a id="be-07"></a>BE-07 | **Índices deixaram de ser dropados a cada boot**: `ensure_categories_collection` fazia `coll.drop_index(...)` de todos os índices (exceto `_id_`) e os recriava em todo startup. Passou a usar `create_index`, que é idempotente (no-op quando o índice já existe). Resolvido junto ao PR #18, sem registro na época; confirmado em 2026-07-16 comparando a main pré-merge (`fb97ac4^1`, que ainda tinha o `drop_index`) com o estado atual. | 2026-07-16 | `c6c1e14` |
| <a id="be-02"></a>BE-02 | **Código morto removido**: `deactivate_category` (sem rota registrada e sem referência em testes) e o import não usado de `jwt_optional` em `products_routes.py`. O `health_controller.check_health` já havia caído no merge do PR #18. A assimetria que isso expôs (dá para reativar, não para desativar) virou [BE-10](#be-10). | 2026-07-16 | `be73cc5` |
| <a id="be-05"></a>BE-05 | **`JWT_ALGORITHM` deixou de ser anunciada**: a var nunca teve efeito (HS256 é fixo no código). Resolvido removendo-a do `.env.example` em vez de torná-la configurável — ler o algoritmo do env exigiria allowlist para barrar `none` (que desliga a verificação de assinatura), HS384/HS512 não agregam aqui e RS256 exigiria par de chaves. O porquê ficou documentado no código. | 2026-07-16 | `56e819b` |
| <a id="mb-08"></a>MB-08 | **Build Android quebrado por `react-native-worklets` órfão**: `react-native-worklets@0.5.1` (exige RN ≥ 0.78) sobrou da atualização para o SDK54 (`c979ccc`) depois que `expo`/`react-native`/`reanimated` foram revertidos ao SDK49. O Gradle reprovava em `:react-native-worklets:assertMinimalReactNativeVersionTask` contra RN 0.72.10, deixando todo PR com o check "Build Android APK" vermelho. Removida a dependência direta (não importada em lugar nenhum — o Reanimated 3.x já embute os worklets). | 2026-07-16 | `a8f10e0` |

---

> **Origem histórica:** a maior parte dos débitos do backend foi identificada no code review de 2026-07-01 e tratada em 6 fases (Fases 1–5 concluídas; a Fase 6 fechou o envelope (BE-01) no PR de débitos técnicos, restando BE-08 e BE-09 como pendências). Os relatórios de trabalho originais foram removidos do repositório após a migração do status para este documento; eles permanecem acessíveis no histórico do git (`docs/code-review-backend.md` e `docs/plano-desenvolvimento-backend.md`, até o commit que os removeu).
