# Decisões de Arquitetura (ADR)

> Fonte: código em `backend/app/utils/network.py` · `mobile/constants/config.ts` · `frontend/src/services/apiConfig.js` · scripts da raiz
> Débitos e divergências: [alinhamento-e-debitos.md](./alinhamento-e-debitos.md)

Registro das decisões arquiteturais do projeto: **o que** foi decidido, **por quê**, quais alternativas foram descartadas e o que a decisão custa. Uma ADR não é documentação de uso — para saber como as coisas funcionam hoje, vá em [arquitetura.md](./arquitetura.md) e [setup-e-deploy.md](./setup-e-deploy.md).

## Como manter

- Uma ADR nova entra **no fim do arquivo**, com o próximo número livre. ADRs existentes **não são editadas** para refletir mudanças de rumo: crie outra que a substitua e mude o `Status` da antiga para `Substituída por ADR-XXXX`.
- Status possíveis: `Aceita` (decidida e implementada), `Aceita — pendente` (decidida, ainda não implementada), `Substituída`, `Rejeitada`.
- Registre aqui só o que é **decisão** (escolha entre caminhos com consequências duradouras). Correção de bug, refactor local e ajuste de doc não viram ADR.

## Índice

| ID | Decisão | Status | Data |
|----|---------|--------|------|
| [ADR-0001](#adr-0001--cada-app-descobre-o-endereço-da-api-por-conta-própria) | Cada app descobre o endereço da API por conta própria | Aceita | 2026-07-25 |
| [ADR-0002](#adr-0002--scripts-de-devrede-como-módulo-local-não-como-lib-publicada) | Scripts de dev/rede como módulo local, não como lib publicada | Aceita — pendente | 2026-07-25 |
| [ADR-0003](#adr-0003--devfull-sobe-os-três-apps) | `dev:full` sobe os três apps | Aceita — pendente | 2026-07-25 |

---

## ADR-0001 — Cada app descobre o endereço da API por conta própria

**Status:** Aceita (implementada em 2026-07-25)

### Contexto

Testar em dispositivo físico exige que o app alcance o backend pelo **IP da máquina na Wi-Fi**, não por `localhost`. Isso era resolvido por um passo manual prévio: `npm run dev` na raiz rodava `sync-network.js`, que detectava o IPv4 e escrevia `network-config.json` na raiz **e** uma cópia em `mobile/network-config.json`. Três consumidores liam esse arquivo — `backend/run.py`, `backend/app/services/email_service.py` e `mobile/constants/config.ts`.

Problemas que motivaram a mudança:

- **O passo era pré-requisito e fácil de esquecer.** Sem rodar a raiz antes, o mobile caía num default `192.168.1.100` e o app simplesmente não conectava, sem erro explicativo.
- **Trocar de rede invalidava tudo.** Era preciso rodar o sync de novo, reiniciar o backend e reiniciar o Metro com `--clear`.
- **A detecção era frágil.** O parsing de `ipconfig` dependia do locale do Windows (`line.includes('Adaptador')` só casa em PT-BR) e tratava adaptadores virtuais (WSL, Docker, Hyper-V, VirtualBox) com a mesma prioridade da Wi-Fi, podendo escolher um IP que o celular não alcança.
- **Estado duplicado.** O mesmo JSON existia em dois lugares, e o frontend web ficava de fora — quem quisesse testar a web pelo celular precisava configurar `VITE_API_URL` à mão.

### Decisão

Cada aplicação descobre o endereço em tempo de execução, no momento em que sobe:

| App | Mecanismo | Onde |
|-----|-----------|------|
| Backend | Socket UDP "conectado" a um IP externo apenas para consultar a tabela de rotas do SO — nenhum pacote é enviado e não há necessidade de internet | `backend/app/utils/network.py` |
| Mobile | Host do dev server (`Constants.expoConfig.hostUri`) — o Metro roda na mesma máquina que o backend, logo o IP que baixou o bundle é o IP da API | `mobile/constants/config.ts` |
| Frontend | `window.location.hostname` — o host pelo qual a página foi aberta | `frontend/src/services/apiConfig.js` |

Decisões de apoio:

- **`network-config.json` deixa de ser pré-requisito** e passa a ser override opcional: o backend ainda respeita `host`/`port` dele, e o mobile o usa como fallback quando não há dev server. O `current_ip` gravado só entra se a detecção falhar, porque pode estar obsoleto.
- **Env vars são o override canônico** — `FLASK_HOST`/`FLASK_PORT`, `VITE_API_URL`, `EXPO_PUBLIC_NETWORK_URL`. No backend elas passam a ter precedência **sobre** o JSON (antes o JSON vencia).
- **O frontend ganha uma fonte única** (`apiConfig.js`, exportando `API_BASE_URL` e `API_URL`), consumida por `api.js` e `auth.js`. A base é normalizada: `VITE_API_URL` é aceita com ou sem o sufixo `/api`.
- **O Vite escuta em todas as interfaces** (`server.host: true`), sem o que a derivação por hostname não teria utilidade — o dev server só respondia em `localhost`.

### Alternativas consideradas

| Alternativa | Por que não |
|-------------|-------------|
| Manter o fluxo com arquivo gerado, só corrigindo os bugs | Não elimina o passo manual nem o ciclo "trocou de rede → regenerar → `--clear`", que é a dor real |
| Publicar a detecção como lib npm de terceiros | Custo de versionamento/publish e dependência de rede no install, para ~10 linhas específicas desta topologia — ver [ADR-0002](#adr-0002--scripts-de-devrede-como-módulo-local-não-como-lib-publicada) |
| Apenas reorganizar os scripts num módulo local | Melhora a organização sem remover o pré-requisito; virou a fase seguinte, não a solução |
| Usar `internal-ip` / `default-gateway` no lugar do socket | Dependência extra para o que `socket` e `os.networkInterfaces()` já resolvem |

### Consequências

**Positivas**

- Subir backend e mobile não exige nenhum passo prévio na raiz; trocar de Wi-Fi não exige regenerar arquivo nem `--clear`.
- A detecção deixa de depender de locale e de heurística sobre nomes de adaptadores: a rota default do SO é a resposta.
- O frontend web entra no mesmo modelo — abrir `http://<ip>:5173` no celular já aponta a API para o mesmo host.
- `run.py` perdeu ~30 linhas de leitura de JSON e `email_service.py` perdeu o bloco de parsing; a lógica de rede passou a ter uma casa única no backend.

**Negativas e limitações conhecidas**

- **`expo start --tunnel` quebra a derivação do mobile:** o `hostUri` passa a ser um host público (`*.exp.direct`), e a API derivada aponta para lá. Nesse modo, defina `EXPO_PUBLIC_NETWORK_URL` explicitamente.
- **O Metro precisa rodar na mesma máquina que o backend.** Essa é a premissa central da decisão; num setup com bundler remoto ela não vale e é preciso usar a env var.
- **Emulador Android depende de salvaguarda:** com `adb reverse` o `hostUri` reporta `localhost`, que dentro do emulador é o próprio emulador. `getNetworkUrl()` trata o caso caindo para `10.0.2.2` (Android) ou `localhost` (iOS). É um caso especial explícito no código, não uma derivação uniforme.
- **`server.host: true` expõe o dev server do frontend na rede local.** É o objetivo declarado (testar de outro dispositivo), mas vale saber que qualquer um na mesma Wi-Fi alcança o Vite.
- **Em produção, `VITE_API_URL` é obrigatória** — a derivação por hostname só atua em `import.meta.env.DEV`.
- Máquina com múltiplas interfaces ativas pode ter divergência entre o IP que o backend anuncia e o que o Expo mostra; o banner do `run.py` e o QR code do Expo servem para comparar.

### Implementação e validação

Arquivos: `backend/app/utils/network.py` (novo), `backend/run.py`, `backend/app/services/email_service.py`, `mobile/constants/config.ts`, `frontend/src/services/apiConfig.js` (novo) + `apiConfig.test.js` (novo), `frontend/src/services/api.js`, `frontend/src/services/auth.js`, `frontend/vite.config.js`.

Validação executada: 193 testes do backend e 34 do frontend passando (5 novos cobrindo a derivação e a normalização de `/api`); `tsc --noEmit` limpo nos arquivos do mobile alterados; boot real do backend com `/api/health` respondendo em `127.0.0.1` **e** pelo IP detectado da LAN. A derivação do `hostUri` **não** foi exercitada em dispositivo/emulador real.

De passagem, a decisão corrigiu uma divergência que causava falha de autenticação: `auth.js` tratava `VITE_API_URL` como se já contivesse `/api`, enquanto `api.js` anexava `/api` — com a variável no formato documentado, o `authService` (login, refresh, exclusão de conta) batia em rotas sem o prefixo.

---

## ADR-0002 — Scripts de dev/rede como módulo local, não como lib publicada

**Status:** Aceita — pendente de implementação

### Contexto

Depois da [ADR-0001](#adr-0001--cada-app-descobre-o-endereço-da-api-por-conta-própria), a raiz ainda tem quatro scripts com responsabilidades sobrepostas: `sync-network.js`, `start-dev.js`, `start-dev.ps1` e `monitor-network.js`. O `.ps1` duplica o `.js` e divergiu dele (tem IP `192.168.0.3` hardcoded e mata **todo** processo Python da máquina); o `monitor-network.js` só imprime "reinicie manualmente". Surgiu a pergunta de empacotar isso como dependência de terceiros e apenas chamá-la no start.

### Decisão

Consolidar em um **módulo local** na raiz, sem publicação: `scripts/dev/` com `network.js` (detecção, função pura e testável), `config.js` (escrita/leitura do override) e `dev.js` (orquestrador). Os scripts do `package.json` passam a chamar esse módulo, e o sync roda embutido no start em vez de ser um passo manual.

### Alternativas consideradas

| Alternativa | Por que não |
|-------------|-------------|
| Publicar como lib npm | Versionamento, `publish` e dependência de rede no install para código que só faz sentido nesta topologia (portas 5000/8081/5173, layout deste monorepo). Sem workspaces na raiz, viraria dependência de um `package.json` que hoje não instala nada |
| Manter os quatro scripts como estão | Duas implementações divergentes do mesmo fluxo, uma delas com um `Stop-Process` global destrutivo |

### Consequências

- Um lugar só para a lógica de rede/dev, com a detecção isolada numa função pura — o ponto que mais quebra onboarding passa a ser testável.
- Fica pendente corrigir, junto: IP hardcoded em `start-dev.ps1:36,48`; `Stop-Process -Name "python"` global em `start-dev.ps1:21`; porta 5000 hardcoded ignorando `config.backend.port` em `sync-network.js:130-132`; falha de detecção sem exit code em `sync-network.js:116` (que anula o `if ($LASTEXITCODE -ne 0)` do `.ps1`); `JSON.parse` sem guard; SIGINT registrado dentro do `setTimeout` e `kill()` que não mata a árvore no Windows em `start-dev.js:36-41`.
- Os `setTimeout` mágicos de 2s/3s devem dar lugar a readiness via `/api/health`, endpoint que já existe.

---

## ADR-0003 — `dev:full` sobe os três apps

**Status:** Aceita — pendente de implementação

### Contexto

`start-dev.js` sobe **backend + mobile**, enquanto `package.json` e a documentação diziam "backend + frontend". Além da divergência, quem trabalha na web precisava subir o Vite à parte.

### Decisão

`npm run dev:full` passa a subir **backend + frontend + mobile**, com logs prefixados por serviço para distinguir a saída dos três processos.

### Consequências

- Um comando cobre o ambiente completo; a discrepância entre script e doc desaparece.
- Três processos no mesmo terminal exigem prefixo de log e encerramento coordenado (Ctrl+C deve derrubar os três, inclusive no Windows, onde `kill()` sobre `shell: true` não alcança o processo filho).
- Quem quiser subir menos continua usando `npm run backend` / `frontend` / `mobile`.
