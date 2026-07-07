# Workflow de commits

Regras de processo para commits neste monorepo. Complementa a seção de **Git** e de **Testes** das [convenções](./convencoes.md).

## Regra principal: rode toda a suíte de testes antes de cada commit

**Todo commit** — seja o fechamento de uma fase de trabalho ou o início de uma nova empreitada — só entra com a suíte de testes **verde**. Antes de `git commit`:

1. Rode os testes de **cada app tocado pelo diff**:

   | App | Comando | Onde |
   |-----|---------|------|
   | Backend | `pytest` | `backend/` |
   | Frontend | `npx vitest run` | `frontend/` |
   | Mobile | `npm test` | `mobile/` |

2. Se qualquer teste falhar, **corrija antes de commitar** — não commite vermelho.
3. Ao corrigir um bug, adicione o teste que o reproduz **no mesmo commit** (ver [convenções → Testes](./convencoes.md)).

> **Por que "cada app tocado":** o backend é a fonte única de verdade do contrato de API; uma mudança nele pode quebrar frontend ou mobile. Quando o diff cruza apps (ex.: mudança de contrato de resposta), rode a suíte dos dois lados antes de commitar.

> **Mudança que altera contrato observável:** além dos testes, valide o fluxo ponta a ponta no app afetado antes de commitar (não confie só na suíte).

## Mensagens: Conventional Commits

Mensagens seguem o padrão [Conventional Commits](https://www.conventionalcommits.org/): `<tipo>(<escopo>): <descrição>`, no imperativo e objetivo.

- **Tipos:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- **Escopo:** app ou área — `backend`, `frontend`, `mobile`, ...
- Commits **pequenos e temáticos**: um assunto por commit.

Exemplos reais do repo:

```
refactor(backend): padroniza envelope de resposta {success, message}
test(backend): autentica testes de escrita com JWT de admin
docs: registra débitos técnicos do backend
```

## Checklist antes de `git commit`

- [ ] Suíte de testes de cada app tocado está **verde**.
- [ ] Bug corrigido tem teste que o reproduz, no mesmo commit.
- [ ] Mensagem no padrão Conventional Commits, imperativa e objetiva.
- [ ] Commit é pequeno e temático (um assunto).
- [ ] Trabalhando em uma branch a partir de `main` (não commitar direto na `main`).
