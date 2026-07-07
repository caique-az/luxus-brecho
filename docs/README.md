# Documentação — Luxus Brechó

Documentação técnica do projeto. Comece pela [arquitetura](./arquitetura.md) para entender o sistema como um todo; depois aprofunde no que precisar.

## Índice

| Documento | O que cobre |
|-----------|-------------|
| [Arquitetura](./arquitetura.md) | Visão geral do monorepo, diagramas, camadas do backend, modelo de dados, autenticação e integrações externas |
| [Referência da API](./api-reference.md) | Todos os endpoints REST: rotas, autenticação, parâmetros e exemplos de payload |
| [Setup e Deploy](./setup-e-deploy.md) | Subir os 3 apps localmente, variáveis de ambiente, rede do mobile e publicação (Vercel/Expo) |
| [Convenções](./convencoes.md) | Padrões de código, estrutura de pastas, autenticação, testes e fluxo de Git |
| [Workflow de commits](./workflow-commits.md) | Rodar a suíte de testes antes de cada commit e padrão Conventional Commits |

## Mapa rápido do repositório

```
luxus-brecho/
├─ backend/      API Flask + MongoDB (fonte única de verdade)
├─ frontend/     Loja web SPA (React + Vite) + painel admin
├─ mobile/       App da loja (Expo / React Native)
├─ docs/         Esta documentação
├─ *.js / *.ps1  Scripts de orquestração e sincronização de rede
└─ CLAUDE.md     Guia rápido de comandos e arquitetura
```

## Em uma frase

E-commerce de brechó (peças únicas) com backend Flask servindo uma API REST consumida por um frontend web e um app mobile independentes. Veja a [arquitetura](./arquitetura.md) para os detalhes.
