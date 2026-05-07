# SPEC_014 — Security Design: Gestão de Segredos, Superfícies de Ataque e Hardening Operacional

**ID:** SPEC_014
**Status:** Concluída
**Data:** 2026-05-05
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução) — AppSec + Backend Sênior
**Skills requeridas:** Python, Docker, segurança de aplicações, auditoria de código, MongoDB
**Depende de:** SPEC_007 (resiliência operacional), SPEC_004 (notificações — token de segredo crítico)

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Security Design — Gestão de Segredos, Superfícies de Ataque e Hardening Operacional.

### 1.2 Resumo (High-Level Definition)

**O que é:** Auditoria estruturada e hardening do sistema Phicube nas dimensões de gestão de segredos, superfícies de ataque externas, segurança de container e rastreabilidade de operações. Produz um checklist executável com critérios de aceite verificáveis por teste ou inspeção.

**Por que estamos fazendo:** O sistema opera com credenciais de exchange (capital real), token Telegram, e acesso a banco de dados. Nenhum desses segredos tem controle formal documentado. Um vazamento de API key resulta em perda financeira direta e irreversível.

**Valor de negócio:** Reduz a superfície de ataque a um nível aceitável para operação com capital real; cria rastreabilidade de auditoria; documenta a postura de segurança do projeto para referência futura.

**Conexão com PRD/SPEC:** PRD §Princípios — "proteção do capital acima de qualquer conveniência técnica"; CLAUDE.md §Notification Pattern — invariante de segurança do token Telegram já declarada; SPEC_007 §6 — logs seguros como requisito.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos (o que será entregue)

- [x] Threat model simplificado documentando atores, vetores e ativos a proteger
- [x] Checklist de controles de segurança com critério de aceite por item
- [x] Auditoria de todas as ocorrências de `str(exc)` no codebase — eliminação ou substituição
- [x] Verificação de autenticação MongoDB em produção
- [x] Revisão do Dockerfile para multi-stage e execução non-root
- [x] Validação de que nenhuma API key ou token aparece em logs em nenhuma condição
- [x] Documentação do procedimento de rotação de segredos

### 2.2 Fora do Escopo (Non-Goals)

- **Não inclui:** Pen test externo ou análise de vulnerabilidades de dependências (escopo de security audit periódico)
- **Não inclui:** Criptografia em repouso no MongoDB (aceito como risco em V1 com mitigação de acesso de rede)
- **Não inclui:** Autenticação de usuários no Dashboard (dashboard é rede privada por design)
- **Não inclui:** WAF ou rate limiting no Dashboard API (não exposto publicamente)

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `CLAUDE.md` | §Notification Pattern | Invariante do token Telegram em logs |
| `SPEC_007` | §6.4 | Logs seguros com `type(exc).__name__` |
| `src/config/settings.py` | todos | Gestão de variáveis de ambiente |
| `docker-compose.yml` | todos | Configuração de container e rede |
| `Dockerfile` | todos | Build e runtime do container |
| `.env.example` | todos | Referência de variáveis necessárias |

---

## 4. Threat Model Simplificado

### 4.1 Ativos a Proteger

| Ativo | Criticidade | Consequência de Comprometimento |
|---|---|---|
| `BINANCE_API_KEY` + `BINANCE_API_SECRET` | Crítica | Perda financeira direta e irreversível |
| `DASHBOARD_API_KEY` + `DASHBOARD_API_SECRET` | Alta | Vazamento de posições e estratégia |
| `TELEGRAM_TOKEN` | Alta | Impersonação do bot, spam, phishing |
| `TELEGRAM_CHAT_ID` | Média | Vazamento de identidade do operador |
| `MONGODB_URI` | Alta | Acesso a todo o histórico de trades e sinais |
| Dados de trades no MongoDB | Alta | Vazamento de estratégia e posições |

### 4.2 Vetores de Ataque Considerados

| Vetor | Probabilidade | Superfície |
|---|---|---|
| Vazamento de segredo em log (texto de exceção) | Alta | `str(exc)` em qualquer módulo que faça chamadas à Binance ou Telegram |
| Container executando como root | Média | Dockerfile sem `USER` não-root |
| MongoDB sem autenticação em produção | Alta | `docker-compose.yml` sem configuração de auth |
| Segredo commitado em `.env` ou código | Média | `.gitignore`, histórico de git |
| Imagem Docker com dependências desnecessárias | Baixa | Dockerfile single-stage |

### 4.3 Atores de Ameaça Considerados

- Acidente interno: desenvolvedor loga `str(exc)` sem intenção — vetor mais provável
- Acesso não autorizado ao host: container root facilita escalada de privilégio
- Acesso ao banco de dados sem autenticação: MongoDB padrão sem auth em `docker-compose`

---

## 5. Checklist de Controles

### CTRL-001 — Nenhum Segredo em Logs

**Descrição:** Nenhuma chamada de rede às APIs Binance, Telegram ou MongoDB deve resultar em log de `str(exc)`, pois URLs com tokens e credenciais ficam embutidas nas mensagens de exceção do `aiohttp` e `ccxt`.

**Critério de Aceite:**
```text
DADO   o codebase completo em src/
QUANDO auditado por grep de str(exc) e log.*str
ENTÃO  zero ocorrências de str(exc) em qualquer except block
E      todas as exceções de rede logadas com type(exc).__name__ e contexto sem credenciais
```

**Como verificar:** `grep -rn "str(exc)" src/` retorna zero resultados após correção.

---

### CTRL-002 — MongoDB com Autenticação em Produção

**Descrição:** O `docker-compose.yml` de produção deve configurar MongoDB com usuário e senha; a URI padrão `mongodb://mongo:27017` sem credenciais é aceitável apenas em ambiente de desenvolvimento local.

**Critério de Aceite:**
```text
DADO   o docker-compose.yml de produção
QUANDO inspecionado
ENTÃO  o serviço mongo tem variáveis MONGO_INITDB_ROOT_USERNAME e MONGO_INITDB_ROOT_PASSWORD
E      o MONGODB_URI em .env.example documenta o formato com autenticação
E      a documentação operacional instrui a nunca usar URI sem credenciais em produção
```

---

### CTRL-003 — Container Non-Root

**Descrição:** O Dockerfile deve criar um usuário não-root e executar o processo do bot sob esse usuário.

**Critério de Aceite:**
```text
DADO   o Dockerfile do projeto
QUANDO inspecionado
ENTÃO  existe instrução `RUN adduser --disabled-password ...` ou equivalente
E      existe instrução `USER <nonroot>` antes do CMD/ENTRYPOINT
E      `docker inspect` na imagem resultante mostra User != root e != ""
```

---

### CTRL-004 — Dockerfile Multi-Stage

**Descrição:** O Dockerfile deve usar multi-stage build para garantir que a imagem de produção não contenha ferramentas de build, pip cache ou dependências de desenvolvimento.

**Critério de Aceite:**
```text
DADO   o Dockerfile do projeto
QUANDO inspecionado
ENTÃO  existe ao menos dois estágios: builder e runtime
E      o estágio runtime copia apenas o necessário do builder
E      a imagem final não contém pip, setuptools ou arquivos de build intermediários
```

---

### CTRL-005 — Arquivo .env Nunca Commitado

**Descrição:** O arquivo `.env` com valores reais nunca deve aparecer no histórico de git.

**Critério de Aceite:**
```text
DADO   o repositório git
QUANDO inspecionado o .gitignore
ENTÃO  `.env` está listado explicitamente
E      `git log --all --full-history -- .env` retorna zero commits com o arquivo
E      `.env.example` existe e documenta todas as variáveis necessárias sem valores reais
```

---

### CTRL-006 — Auditoria de `str(exc)` no Codebase

**Descrição:** Varredura completa do codebase para identificar e corrigir todos os usos de `str(exc)` em blocos de tratamento de exceção, substituindo por `type(exc).__name__` com contexto seguro.

**Critério de Aceite:**
```text
DADO   o codebase em src/ após aplicação deste controle
QUANDO executado: grep -rn "str(exc)\|str(e)\b" src/
ENTÃO  zero resultados em except blocks
```

**Exceção permitida:** `str(exc)` em testes é aceitável quando o objetivo é verificar mensagens de erro.

---

### CTRL-007 — Rotação de Segredos Documentada

**Descrição:** Deve existir procedimento documentado para rotação de cada segredo crítico.

**Critério de Aceite:**
```text
DADO   o arquivo docs/OPERATIONS.md ou equivalente
QUANDO inspecionado
ENTÃO  existe seção "Rotação de Segredos" com procedimento para:
       - BINANCE_API_KEY / BINANCE_API_SECRET
       - TELEGRAM_TOKEN
       - MONGODB_URI (senha)
E      cada procedimento documenta: onde revogar, onde atualizar, como verificar
```

---

### CTRL-008 — Variáveis de Ambiente Validadas na Inicialização

**Descrição:** O sistema não deve iniciar com configuração inválida ou ausente para variáveis críticas.

**Critério de Aceite:**
```text
DADO   que BINANCE_API_KEY está ausente ou vazia
QUANDO o bot é iniciado (python -m src.main)
ENTÃO  o sistema falha na inicialização com mensagem clara sobre a variável ausente
E      nunca tenta conectar à exchange sem credenciais
```

**Como verificar:** `src/config/settings.py` usa `Pydantic BaseSettings` com `Required` (sem default) para variáveis críticas.

---

## 6. Requisitos Funcionais

| ID | Descrição | Prioridade |
|---|---|---|
| RF-001 | Eliminar todos os `str(exc)` em except blocks de src/ | Crítica |
| RF-002 | Dockerfile com multi-stage e execução non-root | Alta |
| RF-003 | MongoDB com auth em docker-compose de produção | Alta |
| RF-004 | `.env` no `.gitignore` e ausente do histórico git | Crítica |
| RF-005 | `.env.example` completo e atualizado | Alta |
| RF-006 | Procedimento de rotação de segredos documentado | Média |
| RF-007 | Teste automatizado que verifica ausência de `str(exc)` em src/ | Média |

---

## 7. Requisitos Não-Funcionais

| ID | Descrição |
|---|---|
| RNF-001 | Auditoria de segurança repetível: checklist pode ser re-executado a cada release |
| RNF-002 | Nenhum controle depende de ferramenta externa paga |
| RNF-003 | Controles CTRL-001 e CTRL-006 são verificáveis por grep automatizado no CI |

---

## 8. Cenários e Casos de Borda

| ID | Cenário | Comportamento Esperado |
|---|---|---|
| CE-001 | `ccxt.NetworkError` com URL contendo API key no traceback | `type(exc).__name__` logado; URL nunca aparece em log |
| CE-002 | `aiohttp.ClientError` com token Telegram na URL | Mesmo tratamento — `type(exc).__name__` exclusivamente |
| CE-003 | Bot iniciado sem TELEGRAM_TOKEN | `NullNotifier` instanciado; log INFO sem revelar ausência de forma que exponha outros segredos |
| CE-004 | MongoDB URI com senha na string de conexão em log de startup | URI nunca logada completa — apenas host e nome do banco |
| CE-005 | Container reiniciado por crash — uid do processo após restart | `USER` definido no Dockerfile garante persistência do non-root independente de restart |

---

## 9. Critérios de Aceite Consolidados e DoD

### Definição de Pronto (DoD)

- [x] `grep -rn "str(exc)" src/` retorna zero resultados em except blocks
- [x] Dockerfile com multi-stage implementado e imagem de produção sem ferramentas de build
- [x] Dockerfile com `USER nonroot` — `docker inspect` confirma
- [x] `docker-compose.yml` com autenticação MongoDB configurada para produção
- [x] `.env` no `.gitignore`; ausente do histórico git
- [x] `.env.example` atualizado com todas as variáveis e comentários de uso
- [x] `docs/OPERATIONS.md` com seção de rotação de segredos
- [x] Teste de auditoria `tests/security/test_no_str_exc.py` passando no CI
- [x] `docs/SDD/README.md` atualizado com SPEC_014
- [x] `ruff check src/ tests/` sem erros nos módulos de segurança

---

## 10. Decisões de Design

| ID | Decisão | Justificativa |
|---|---|---|
| DD-001 | Criptografia em repouso do MongoDB fora de escopo V1 | Complexidade desproporcional para V1; mitigado por acesso de rede restrito ao docker network interno |
| DD-002 | Dashboard sem autenticação por design | Dashboard exposto apenas em rede privada; auth aumentaria complexidade sem mitigar risco real |
| DD-003 | Auditoria de `str(exc)` como teste automatizado no CI | Regressão de segurança mais provável do projeto — deve ser detectada automaticamente |
| DD-004 | Sem WAF ou rate limiting no Dashboard | Superfície de ataque é interna; complexidade não justificada |

---

## 11. Riscos

| Risco | Impacto | Probabilidade | Mitigação |
|---|---|---|---|
| API key vazada em log antes da correção | Crítico — perda financeira | Média | Prioridade máxima de execução do CTRL-001 e CTRL-006 |
| MongoDB sem auth exposto por erro de configuração | Alto | Média | CTRL-002 com verificação automatizada |
| Segredo commitado acidentalmente por outro desenvolvedor | Alto | Baixa | CTRL-005 + hook de pre-commit com `detect-secrets` (recomendado) |
| Rotação de segredos não executada após incidente | Alto | Baixa | CTRL-007 documenta procedimento; operador deve executar |

---

## Histórico

- **2026-05-05:** Criação da SPEC_014 pelo Time A.
- **2026-05-06:** Todos os controles verificados e DoD atendido. Status: Concluída.
