# Documentação — Luxus Brechó

Documentação técnica do projeto: e-commerce de brechó (**peças únicas**) com backend Flask servindo uma API REST consumida por um frontend web e um app mobile independentes.

Esta documentação descreve o **estado atual do código** — incluindo divergências e débitos conhecidos, que vivem num único lugar: [alinhamento-e-debitos.md](./alinhamento-e-debitos.md).

## Por onde começar

- **Quero entender o sistema** → [arquitetura.md](./arquitetura.md) (monorepo, camadas, dados, auth, boot).
- **Quero consumir a API** → [api-reference.md](./api-reference.md) (contrato geral) e depois o recurso específico em [`api/`](./api/).
- **Quero mexer num app** → o doc do app em [`apps/`](./apps/), começando pela seção de débitos dele.
- **Quero subir o ambiente** → [setup-e-deploy.md](./setup-e-deploy.md).

## Índice completo

| Documento | O que cobre |
|-----------|-------------|
| [arquitetura.md](./arquitetura.md) | Visão geral do monorepo, camadas do backend, modelo de dados e índices, autenticação, rede e deploy |
| [api-reference.md](./api-reference.md) | Contrato geral da API: auth JWT, formatos de resposta reais, paginação, erros, rate limiting + índice dos recursos |
| [api/users-auth.md](./api/users-auth.md) | Usuários e autenticação (17 endpoints): registro, login/refresh, confirmação de e-mail, exclusão de conta |
| [api/products.md](./api/products.md) | Produtos (8): listagem/busca, CRUD admin, fluxos com imagem |
| [api/categories.md](./api/categories.md) | Categorias (7): leitura pública, escrita admin, cache |
| [api/cart.md](./api/cart.md) | Carrinho (5): peça única, add idempotente, sync |
| [api/orders.md](./api/orders.md) | Pedidos (5): criação transacional, status, cancelamento |
| [api/favorites.md](./api/favorites.md) | Favoritos (5): JWT, toggle, produto embutido |
| [api/images.md](./api/images.md) | Imagens (5): Supabase Storage, uploads admin |
| [api/health.md](./api/health.md) | Health (2): status da API |
| [apps/backend.md](./apps/backend.md) | Backend por dentro: utils, services, entrypoints, testes e limitações |
| [apps/frontend.md](./apps/frontend.md) | Frontend web: rotas, stores Zustand, interceptors do axios, testes |
| [apps/mobile.md](./apps/mobile.md) | Mobile: estado real (sem JWT, carrinho com `quantity`, checkout órfão) |
| [alinhamento-e-debitos.md](./alinhamento-e-debitos.md) | **Doc vivo** — matriz de alinhamento Backend×Web×Mobile e todos os débitos conhecidos, com ID |
| [setup-e-deploy.md](./setup-e-deploy.md) | Subir os 3 apps, **tabela canônica de env vars**, rede do mobile e publicação (Vercel/Expo) |
| [convencoes.md](./convencoes.md) | Padrões de código, API, auth, testes, Git e **convenções de documentação** |

## Mapa rápido do repositório

```
luxus-brecho/
├─ backend/      API Flask + MongoDB (fonte única de verdade)
├─ frontend/     Loja web SPA (React + Vite) + painel admin
├─ mobile/       App da loja (Expo / React Native)
├─ docs/         Esta documentação
├─ security-tests/  Smoke test de segurança (security-analyzer.py)
├─ *.js / *.ps1  Scripts de orquestração (npm run dev = sync de rede; dev:full = backend + mobile)
└─ CLAUDE.md     Guia operacional do agente de código (não substitui docs/)
```

## Como manter esta documentação

Regras completas em [convencoes.md § Convenções de documentação](./convencoes.md#convenções-de-documentação). O resumo: documente a **realidade** do código (o ideal vira débito registrado), declare a fonte de cada afirmação, mantenha cada fato numa casa única, e — ao mudar rota/decorator/shape — atualize o `docs/api/*.md` correspondente no mesmo PR. Todo documento novo entra neste índice no mesmo commit.
