---
name: git-commit-push
description: Workflow replicado de .claude/commands/git-commit-push.md para 'Git Commit & Push'. Use quando precisar executar esse procedimento no projeto Binance Phicube.
---

# Git Commit & Push

Versiona todas as alterações pendentes do repositório, atualiza o `.gitignore` se necessário e envia para a branch `main` remota.

**Argumento opcional:** mensagem de commit (gerada automaticamente se omitida seguindo Conventional Commits).

## Procedimento

### 1. Inspecionar o estado atual

```bash
git status
```

Identificar: arquivos modificados rastreados, novos não rastreados, deletados.

### 2. Identificar o que não deve ser versionado

| Categoria | Exemplos |
|-----------|----------|
| Logs | `*.log`, `logs/`, `*.log.*` |
| Cache Python | `__pycache__/`, `*.pyc`, `*.pyo`, `.pytest_cache/`, `.ruff_cache/` |
| Ambiente virtual | `.venv/`, `venv/`, `env/` |
| Build / dist | `dist/`, `build/`, `*.egg-info/` |
| Segredos | `.env` (apenas `.env.example` deve ser versionado) |
| IDEs | `.idea/`, `.vscode/settings.json` |
| Dados locais | `*.db`, `*.sqlite`, dumps de MongoDB |
| Cobertura de testes | `.coverage`, `htmlcov/`, `coverage.xml` |

### 3. Atualizar o `.gitignore`

Para cada artefato não coberto, adicionar ao `.gitignore`. Se já rastreado pelo Git, remover do índice:

```bash
git rm --cached <arquivo-ou-pasta>
# Para pastas:
git rm -r --cached <pasta>/
```

### 4. Adicionar ao stage

```bash
git add -A
git status  # confirmar que apenas itens corretos estão no stage
```

### 5. Gerar a mensagem de commit

> **Mensagens de commit sempre em inglês** — única exceção ao idioma pt-BR do projeto.

```
<type>(<scope>): <short description in imperative>
```

Tipos válidos: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `ci`, `perf`, `style`, `revert`

**Escopos do projeto:**

| Escopo | Quando usar |
|--------|-------------|
| `bot` | Lógica principal do monitor (`main.py`) |
| `signal-engine` | Detecção e avaliação de sinais |
| `indicators` | Alligator, AO, Fractais |
| `risk-manager` | Cálculo de tamanho de posição |
| `order-manager` | Execução de ordens na Binance |
| `exchange` | Cliente ccxt / BinanceClient |
| `storage` | Repositório MongoDB |
| `config` | Configurações e variáveis de ambiente |
| `docker` | Dockerfile, docker-compose |
| `tests` | Adição ou correção de testes |
| `team` | Documentação de time |
| `ci` | Pipelines de CI/CD |

Exemplos:
```
feat(signal-engine): add fractal lookback limit of 100 candles
fix(order-manager): cancel all orders when SL placement fails
docs: update SDD README with SPEC_006 status
test(indicators): add edge case for flat AO values
```

### 6. Executar o commit

```bash
git commit -m "<mensagem>"
```

### 7. Push para main

```bash
git push origin main
```

Se rejeitado por divergência:
```bash
git pull --rebase origin main
git push origin main
```

> ⚠️ **Nunca usar `--force` sem confirmação explícita do usuário.**

### 8. Confirmar

Informar: branch, commit hash (curto), arquivos alterados.

## Critérios de Conclusão

- [ ] `git status` mostra working tree limpa após o push
- [ ] Nenhum arquivo sensível (`.env`, segredos, chaves) foi commitado
- [ ] `.gitignore` cobre todos os artefatos identificados
- [ ] Push retornou exit code 0

