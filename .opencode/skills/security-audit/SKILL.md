---
name: security-audit
description: 'Workflow de auditoria de segurança AppSec para o projeto Phicube. Use quando adicionar dependências, mudar o Dockerfile ou docker-compose.yml, alterar variáveis de ambiente, revisar o .gitignore, ou antes de qualquer release para produção. Cobre: segredos, dependências vulneráveis, containers, portas expostas e controle de acesso.'
argument-hint: 'Escopo da auditoria (ex: "dependências", "docker", "release completo")'
---

# Auditoria de Segurança — Phicube

Workflow de revisão de segurança para o bot de trading. Uma API Key comprometida significa perda financeira imediata — esta auditoria é obrigatória antes de qualquer release para produção.

## Quando Usar

- Antes de qualquer release para produção
- Ao adicionar dependência nova ao `pyproject.toml`
- Ao alterar `docker-compose.yml` ou `Dockerfile`
- Ao alterar `.gitignore` ou variáveis de ambiente
- Ao suspeitar de vazamento de segredos

## Procedimento

### 1. Verificar segredos no repositório

```bash
# Checar se .env está sendo ignorado corretamente
git status
git ls-files | grep -i "\.env"

# Verificar histórico por segredos acidentais
git log --all --full-history -- "**/.env"

# Scan de segredos no código (se gitleaks disponível)
gitleaks detect --source . --verbose
```

Confirme:
- [ ] `.env` não aparece em `git ls-files`
- [ ] `.env` está no `.gitignore`
- [ ] `.env.example` existe e não contém valores reais de produção
- [ ] Nenhuma API Key, senha ou token hardcoded no código-fonte
- [ ] Logs não imprimem valores de `api_key`, `api_secret` ou credenciais MongoDB

### 2. Verificar dependências vulneráveis

```bash
pip-audit
```

Ou, se não instalado:
```bash
pip install pip-audit && pip-audit
```

Confirme:
- [ ] Nenhuma dependência com vulnerabilidade crítica ou alta
- [ ] Vulnerabilidades médias documentadas com plano de atualização
- [ ] Versões das dependências principais auditadas: `ccxt`, `motor`, `pydantic`, `aiohttp`

### 3. Verificar segurança do Dockerfile e containers

Leia `docker/Dockerfile` e `docker-compose.yml` e confirme:
- [ ] Container `phicube-bot` roda com usuário não-root (`USER phicube` ou equivalente)
- [ ] Nenhuma porta desnecessária exposta ao host no serviço `phicube-bot`
- [ ] MongoDB não expõe a porta 27017 ao host em produção (somente na rede interna Docker)
- [ ] `mongo-express` está com `profiles: ["dev"]` — nunca disponível sem o perfil explícito
- [ ] Sem `privileged: true` nos containers
- [ ] Imagem base usa versão específica (não `:latest`)

### 4. Verificar variáveis de ambiente e configuração

Leia `src/config/settings.py` e confirme:
- [ ] Todos os segredos são carregados via `pydantic-settings` de variáveis de ambiente
- [ ] `BINANCE_TESTNET=True` por padrão — exige mudança explícita para produção
- [ ] MongoDB URI não usa credenciais padrão (`root`/`root`) em produção
- [ ] Nenhum campo sensível tem valor padrão hardcoded no código

### 5. Verificar controle de acesso

Confirme:
- [ ] Dashboard (se existir) requer autenticação antes de exibir dados
- [ ] API interna do bot não está exposta sem autenticação
- [ ] Acesso ao servidor de produção por SSH com chave — sem senha root

### 6. Verificar scan da imagem Docker (se Trivy disponível)

```bash
trivy image binance-phicube:latest
```

Confirme:
- [ ] Sem vulnerabilidades críticas nas camadas da imagem
- [ ] Resultado documentado antes do deploy

## Critérios de Conclusão

- [ ] Nenhum segredo no repositório ou no código
- [ ] `pip-audit` sem vulnerabilidades críticas/altas
- [ ] Containers rodando com usuário não-root e sem portas desnecessárias expostas
- [ ] `mongo-express` indisponível sem perfil `dev`
- [ ] Resultado da auditoria comunicado ao AppSec e ao Backend Sênior
