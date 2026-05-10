---
name: git-commit-push
description: 'Use quando solicitar commit das alterações, enviar para o repositório remoto, fazer push, versionar mudanças ou sincronizar com o GitHub. Executa: verificação do status, limpeza do .gitignore, inclusão de todas as alterações pendentes, commit com mensagem seguindo Conventional Commits e push para a branch main.'
argument-hint: 'Mensagem de commit (opcional — será gerada automaticamente se omitida)'
---

# Git Commit & Push

Versiona todas as alterações pendentes do repositório, atualiza o `.gitignore` se necessário e envia para a branch `main` remota.

## Quando Usar

- "Faz o commit das alterações"
- "Envia para o GitHub"
- "Faz o push"
- "Versiona tudo"
- "Commit e push"

## Procedimento

### 1. Inspecionar o estado atual

Execute `git status` para identificar:
- Arquivos modificados rastreados (`modified`)
- Arquivos novos não rastreados (`untracked`)
- Arquivos deletados

```bash
git status
```

### 2. Identificar o que não deve ser versionado

Analise os itens listados e identifique artefatos que **não devem entrar no repositório**:

| Categoria | Exemplos |
|-----------|----------|
| Logs | `*.log`, `logs/`, `*.log.*` |
| Cache Python | `__pycache__/`, `*.pyc`, `*.pyo`, `.pytest_cache/`, `.ruff_cache/` |
| Ambiente virtual | `.venv/`, `venv/`, `env/` |
| Artefatos Docker | `.dockerignore` sobrescreve, mas verificar `*.tar`, imagens exportadas |
| Build / dist | `dist/`, `build/`, `*.egg-info/` |
| Segredos | `.env` (apenas `.env.example` deve ser versionado) |
| IDEs | `.idea/`, `.vscode/settings.json` (exceto extensões recomendadas) |
| Dados locais | `*.db`, `*.sqlite`, dumps de MongoDB |
| Cobertura de testes | `.coverage`, `htmlcov/`, `coverage.xml` |

### 3. Atualizar o `.gitignore`

Para cada artefato identificado no passo 2 que **ainda não esteja** no `.gitignore`:

- Abra o arquivo `.gitignore` na raiz do projeto
- Adicione as entradas necessárias, agrupadas por categoria com comentários
- Salve o arquivo

Se o artefato já estava sendo rastreado pelo Git (aparece como `modified` ou `tracked`), remova-o do índice sem deletar do disco:

```bash
git rm --cached <arquivo-ou-pasta>
# Para pastas recursivamente:
git rm -r --cached <pasta>/
```

### 4. Adicionar todas as alterações ao stage

Após limpar o `.gitignore`, rastreie tudo o que deve ser versionado:

```bash
git add -A
```

Verifique o resultado com `git status` para confirmar que apenas os itens corretos estão no stage.

Se houver itens indesejados no stage, remova-os:

```bash
git restore --staged <arquivo>
```

### 5. Gerar a mensagem de commit

Se o usuário forneceu uma mensagem como argumento, use-a diretamente.

Se não forneceu, gere uma mensagem seguindo o padrão **Conventional Commits**.

> **Atenção:** mensagens de commit são sempre em **inglês** — esta é a única exceção ao idioma pt-BR do projeto, aceita pelo time para compatibilidade com o padrão internacional Conventional Commits.

```
<type>(<scope>): <short description in imperative>

<optional body: explain WHY, not what>

<optional footer: BREAKING CHANGE, issue refs>
```

Tipos válidos: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `ci`, `perf`, `style`, `revert`

#### Regras obrigatórias de nomenclatura

| Campo | Regra |
|-------|-------|
| `type` | Minúsculo, pertencente à lista válida acima |
| `scope` | Curto, técnico, em `kebab-case` — ver tabela abaixo |
| `description` | Inglês, imperativo, inicial minúscula, sem ponto final |
| Título completo | Máximo 72 caracteres |

**Escopos recomendados para este projeto:**

| Escopo | Quando usar |
|--------|-------------|
| `bot` | Lógica principal do monitor de trading (`main.py`) |
| `signal-engine` | Detecção e avaliação de sinais |
| `indicators` | Cálculo de indicadores técnicos (Alligator, AO, Fractais) |
| `risk-manager` | Cálculo de tamanho de posição |
| `order-manager` | Execução de ordens na Binance |
| `exchange` | Cliente ccxt / BinanceClient |
| `storage` | Repositório MongoDB |
| `config` | Configurações e variáveis de ambiente |
| `docker` | Dockerfile, docker-compose, .dockerignore |
| `tests` | Adição ou correção de testes |
| `team` | Documentação de time |
| `ci` | Pipelines de CI/CD |

**Mudanças incompatíveis (breaking change):** usar `!` após o tipo/escopo e incluir rodapé `BREAKING CHANGE:` com descrição da quebra.

Evitar mensagens genéricas como `update files`, `fix stuff`, `changes` ou `wip`.

**Exemplos** (sempre em inglês, conforme convenção do projeto):

```
feat(team): add full team directory structure (10 professionals, 30 files)
chore: update .gitignore to exclude logs and cache
feat(bot): implement trading monitor and order execution
fix(signal-engine): prevent duplicate signal execution for same symbol
refactor(risk-manager): simplify position size rounding
test(indicators): add edge case tests for fractal detection
docs: update README with Docker setup instructions
build(docker): add multi-stage Dockerfile with non-root user
```

Para commits que abrangem múltiplos contextos da sessão, use o escopo mais abrangente ou omita-o:

```
chore: clean repository and add all pending changes
```

### 6. Executar o commit

```bash
git commit -m "<mensagem gerada ou fornecida>"
```

### 7. Push para main

```bash
git push origin main
```

Se o push for rejeitado por divergência (non-fast-forward):

1. Execute `git pull --rebase origin main`
2. Resolva conflitos se houver
3. Execute `git push origin main` novamente

> ⚠️ **Nunca use `--force` ou `--force-with-lease` sem confirmação explícita do usuário.**

### 8. Confirmar

Após o push bem-sucedido, informe:
- Branch: `main`
- Commit hash (curto)
- Quantos arquivos foram alterados
- Link para o repositório no GitHub se disponível

## Critérios de Conclusão

- [ ] `git status` mostra working tree limpa após o push
- [ ] Nenhum arquivo sensível (`.env`, segredos, chaves) foi commitado
- [ ] `.gitignore` cobre todos os artefatos identificados
- [ ] Push retornou exit code 0
