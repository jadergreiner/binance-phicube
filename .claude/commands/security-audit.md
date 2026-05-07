# Auditoria de Segurança — Phicube

Workflow de revisão de segurança para o bot de trading. Uma API Key comprometida significa perda financeira imediata — esta auditoria é obrigatória antes de qualquer release para produção.

**Argumento:** escopo da auditoria (ex: `"dependências"`, `"docker"`, `"release completo"`)

## Quando Usar

- Antes de qualquer release para produção
- Ao adicionar dependência nova ao `pyproject.toml`
- Ao alterar `docker-compose.yml` ou `Dockerfile`
- Ao alterar `.gitignore` ou variáveis de ambiente
- Ao suspeitar de vazamento de segredos

## Procedimento

### 1. Verificar segredos no repositório

```bash
git status
git ls-files | grep -i "\.env"
git log --all --full-history -- "**/.env"
```

- [ ] `.env` não aparece em `git ls-files`
- [ ] `.env` está no `.gitignore`
- [ ] `.env.example` existe e não contém valores reais de produção
- [ ] Nenhuma API Key, senha ou token hardcoded no código-fonte
- [ ] Logs não imprimem valores de `api_key`, `api_secret` ou credenciais MongoDB
- [ ] `aiohttp.ClientError` logado com `type(exc).__name__` — nunca `str(exc)` (token vaza via URL)

### 2. Verificar dependências vulneráveis

```bash
pip-audit
```

- [ ] Nenhuma dependência com vulnerabilidade crítica ou alta
- [ ] Vulnerabilidades médias documentadas com plano de atualização
- [ ] Versões principais auditadas: `ccxt`, `motor`, `pydantic`, `aiohttp`

### 3. Verificar segurança do Dockerfile e containers

Ler `docker/Dockerfile` e `docker-compose.yml`:

- [ ] Container `phicube-bot` roda com usuário não-root (`USER phicube`)
- [ ] Nenhuma porta desnecessária exposta ao host no serviço `phicube-bot`
- [ ] MongoDB não expõe a porta 27017 ao host em produção (apenas rede interna Docker)
- [ ] `mongo-express` está com `profiles: ["dev"]` — nunca disponível sem perfil explícito
- [ ] Sem `privileged: true` nos containers
- [ ] Imagem base usa versão específica (não `:latest`)

### 4. Verificar variáveis de ambiente e configuração

Ler `src/config/settings.py`:

- [ ] Todos os segredos são carregados via `pydantic-settings` de variáveis de ambiente
- [ ] `BINANCE_TESTNET=True` por padrão — exige mudança explícita para produção
- [ ] MongoDB URI não usa credenciais padrão em produção
- [ ] Nenhum campo sensível tem valor padrão hardcoded no código

### 5. Verificar controle de acesso

- [ ] Dashboard requer autenticação (credenciais separadas das de trading)
- [ ] API interna do bot não está exposta sem autenticação
- [ ] Acesso ao servidor de produção por SSH com chave

### 6. Verificar scan da imagem Docker (se Trivy disponível)

```bash
trivy image binance-phicube:latest
```

- [ ] Sem vulnerabilidades críticas nas camadas da imagem

## Critérios de Conclusão

- [ ] Nenhum segredo no repositório ou no código
- [ ] `pip-audit` sem vulnerabilidades críticas/altas
- [ ] Containers rodando com usuário não-root e sem portas desnecessárias expostas
- [ ] `mongo-express` indisponível sem perfil `dev`
- [ ] Resultado comunicado ao AppSec e ao Backend Sênior
