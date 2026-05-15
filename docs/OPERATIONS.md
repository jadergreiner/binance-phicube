# Manual Operacional — Binance Phicube

**Versão:** 1.0
**Data:** 2026-05-06
**Referência:** SPEC_014 — Security Design

---

## Rotacao de Segredos

Este documento descreve o procedimento obrigatorio para rotacao de cada segredo critico do sistema. Execute este procedimento sempre que:

- Um colaborador com acesso for removido da equipe
- Houver suspeita de comprometimento de qualquer credencial
- A politica de rotacao periodica exigir (recomendado: a cada 90 dias para producao)

---

### BINANCE_API_KEY / BINANCE_API_SECRET

**Criticidade:** Critica — comprometimento resulta em perda financeira direta e irreversivel.

#### Onde revogar

1. Acesse [https://www.binance.com](https://www.binance.com) (Mainnet) ou [https://testnet.binancefuture.com](https://testnet.binancefuture.com) (Testnet).
2. Va em: Perfil > Gerenciamento de API (API Management).
3. Localize a API Key comprometida ou a ser rotacionada.
4. Clique em "Deletar" para revogar imediatamente.
5. Crie uma nova API Key com as mesmas permissoes (Futures READ + TRADE para o bot; somente READ para o dashboard).
6. Configure a whitelist de IP com o IP de saida do servidor de producao.

#### Onde atualizar

1. No servidor de producao, edite o arquivo `.env`:
   ```
   BINANCE_API_KEY=<nova_chave>
   BINANCE_API_SECRET=<novo_segredo>
   ```
2. Para o dashboard (credencial separada, somente leitura):
   ```
   DASHBOARD_API_KEY=<nova_chave_readonly>
   DASHBOARD_API_SECRET=<novo_segredo_readonly>
   ```
3. Reinicie os containers:
   ```bash
   docker compose down && docker compose up -d
   ```

#### Como verificar

```bash
# Verificar se o bot conectou com sucesso — procurar log de inicializacao sem erros de auth
docker compose logs phicube | grep -i "inicializando\|autenticacao\|auth"

# Verificar se o dashboard esta operacional
curl -s http://localhost:8080/health
```

Confirmar ausencia de erros `AuthenticationError` ou `InvalidApiKey` nos logs.

---

### TELEGRAM_TOKEN

**Criticidade:** Alta — comprometimento permite impersonacao do bot, envio de mensagens falsas ao operador e phishing.

#### Onde revogar

1. Abra o Telegram e acesse o [@BotFather](https://t.me/BotFather).
2. Envie o comando `/mybots` e selecione o bot comprometido.
3. Va em "API Token" > "Revoke current token".
4. O BotFather gerara um novo token imediatamente.

#### Onde atualizar

1. No servidor de producao, edite o arquivo `.env`:
   ```
   TELEGRAM_TOKEN=<novo_token>
   ```
2. Reinicie o container do bot:
   ```bash
   docker compose restart phicube
   ```

#### Como verificar

```bash
# Verificar se o notifier inicializou corretamente
docker compose logs phicube | grep -i "telegram\|notifier"
```

Envie uma mensagem de teste via bot para confirmar recepcao. Confirmar que o token antigo nao responde mais a requisicoes.

---

### MONGODB_URI (senha do banco de dados)

**Criticidade:** Alta — comprometimento expoe todo o historico de trades, sinais e dados de auditoria.

#### Onde revogar

A senha do MongoDB nao tem revogacao direta pela Binance ou por servico externo — ela e gerenciada localmente no proprio container.

1. Acesse o container MongoDB:
   ```bash
   docker compose exec mongo mongosh -u <usuario_atual> -p <senha_atual> --authenticationDatabase admin
   ```
2. Altere a senha do usuario administrador:
   ```javascript
   db.adminCommand({
     updateUser: "<MONGO_INITDB_ROOT_USERNAME>",
     pwd: "<nova_senha_forte>"
   })
   ```
3. Saia do mongosh com `exit`.

#### Onde atualizar

1. No servidor de producao, edite o arquivo `.env`:
   ```
   MONGO_INITDB_ROOT_PASSWORD=<nova_senha_forte>
   ```
   O `MONGODB_URI` e interpolado automaticamente pelo `docker-compose.yml` a partir das variaveis `MONGO_INITDB_ROOT_USERNAME` e `MONGO_INITDB_ROOT_PASSWORD`.

2. Reinicie os containers que dependem do MongoDB:
   ```bash
   docker compose restart phicube dashboard-api
   ```
   Nao reinicie o container `mongo` neste passo — a senha ja foi alterada diretamente no banco.

#### Como verificar

```bash
# Testar conexao com a nova senha
docker compose exec mongo mongosh \
  -u <MONGO_INITDB_ROOT_USERNAME> \
  -p <nova_senha_forte> \
  --authenticationDatabase admin \
  --eval "db.adminCommand('ping')"

# Verificar logs do bot para confirmar reconexao ao MongoDB
docker compose logs phicube | grep -i "mongo\|repositorio\|conexao"
```

Confirmar ausencia de erros `AuthenticationFailed` nos logs.

---

## Verificacao Pos-Rotacao

Apos rotacionar qualquer segredo, execute a seguinte lista de verificacao:

- [ ] Container do bot (`phicube`) em status `running` — `docker compose ps`
- [ ] Container do dashboard (`phicube-dashboard-api`) em status `running`
- [ ] Endpoint `/health` retorna HTTP 200 — `curl http://localhost:8080/health`
- [ ] Logs do bot sem erros de autenticacao nos ultimos 5 minutos
- [ ] (Se Telegram rotacionado) Notificacao de teste recebida com sucesso
- [ ] (Se MongoDB rotacionado) Nenhum erro de conexao com banco nos logs

---

## Principios de Seguranca Operacional

1. **Nunca reutilize credenciais entre ambientes** — Testnet e Mainnet devem ter API Keys distintas.
2. **Nunca compartilhe o arquivo `.env`** via Slack, e-mail ou qualquer canal nao criptografado.
3. **O `.env` nunca deve ser commitado** no repositorio git — verificar com `git status` antes de qualquer commit.
4. **Dashboard usa API Key separada com permissao somente leitura** — nunca use as credenciais do bot no dashboard.
5. **URI do MongoDB nunca deve aparecer em logs** — apenas host e nome do banco sao aceitaveis em mensagens de log.
6. **Rotacao preventiva a cada 90 dias** para todos os segredos de producao.

---

*Referencia: SPEC_014 — Security Design (docs/SDD/SPEC_014_SECURITY_DESIGN/SPEC.md)*

---

## Resposta a Alerta de SL Orfao

**Referencia:** SPEC_015 — Monitoramento de SL Orfao (docs/SDD/SPEC_015_SL_ORFAO_INTERVENCAO_ASSISTIDA/SPEC.md)

### O que e o alerta

O bot detecta periodicamente (ciclo de 60 segundos) se cada posicao aberta possui uma ordem de Stop Loss ativa na exchange. Quando o SL desaparece (cancelado, expirado ou rejeitado), um alerta CRITICO e enviado via Telegram:

```
🚨 SL AUSENTE — ACAO NECESSARIA
Simbolo: BTCUSDT
SL esperado: $82.150,00
Preco atual: $82.890,00
Distancia: 0,90%
```

Se nao houver resposta, **re-alertas sao enviados a cada 15 minutos** com o contador de alertas e o tempo total desprotegido.

### Protocolo de Resposta

**Ao receber qualquer alerta de SL ORPHAN:**

1. **Verifique se a posicao ainda esta aberta** na Binance (Futures > Posicoes).

2. **Se a posicao ja foi fechada:** aguarde o proximo ciclo (60 s). O bot detectara automaticamente e encerrara os alertas.

3. **Se a posicao esta aberta**, avalie o risco imediato:
   - Veja o preco atual e o SL esperado informado no alerta.
   - Calcule a distancia percentual: quanto o preco pode cair/subir antes de atingir o SL esperado.
   - **Se o risco for inaceitavel:** feche a posicao imediatamente (passo 5).

4. **Para recolocar o SL:**
   - Acesse Binance Futures > Simbolo afetado.
   - Crie uma ordem **Stop Market** no lado oposto a posicao.
   - Marque `reduceOnly=true` para garantir que a ordem nao abra nova posicao.
   - Use o preco de SL informado no alerta como referencia.

5. **Para fechar manualmente:**
   - Acesse Binance Futures > Simbolo afetado.
   - Crie uma ordem **Market** com `reduceOnly=true`.
   - Confirme que a posicao foi zerada antes de sair.

6. **Confirmacao:** o bot envia uma notificacao informativa "SL RESTAURADO" com o tempo de resposta assim que detectar a normalizacao.

### Configuracao do Intervalo de Re-alerta

```dotenv
# Minimo: 5 minutos. Padrao: 15 minutos.
SL_MISSING_RENOTIFY_INTERVAL_MINUTES=15
```

### Registro de Auditoria

Cada evento de SL orfao e registrado no MongoDB com:
- `sl_missing_first_detected_at` — timestamp do primeiro alerta
- `sl_restored_at` — timestamp da normalizacao
- `sl_missing_response_time_seconds` — tempo de resposta em segundos
- `sl_missing_notification_count` — quantos alertas foram enviados

Use esses campos para analisar tendencias de resposta e ajustar o intervalo se necessario.

> **Nunca ignore alertas de SL ORPHAN. Cada minuto sem protecao e risco nao coberto.**

---

## Procedimento de Restore — MongoDB

**Referencia:** SPEC_031 — Backup Automatico MongoDB (docs/SDD/SPEC_031_BACKUP_MONGODB/SPEC.md)

O bot executa backup diario automatico do MongoDB as 03:00 UTC para o diretorio `./backups/mongo/`.

### Listar backups disponiveis

```bash
ls -lh ./backups/mongo/phicube_*.gz
```

Ou via Docker:

```bash
docker compose exec phicube ls -lh /app/backups/mongo/
```

### Restaurar o backup mais recente

```bash
mongorestore "mongodb://<usuario>:<senha>@localhost:27017/phicube" \
  --gzip --archive="./backups/mongo/$(ls -t ./backups/mongo/phicube_*.gz | head -1)" \
  --drop
```

### Restaurar um backup especifico

```bash
mongorestore "mongodb://<usuario>:<senha>@localhost:27017/phicube" \
  --gzip --archive="./backups/mongo/phicube_2026-05-10.gz" \
  --drop
```

### Restaurar via Docker

```bash
docker compose exec -T phicube mongorestore "mongodb://mongo:27017/phicube" \
  --gzip --archive="/app/backups/mongo/phicube_2026-05-10.gz" \
  --drop
```

O parametro `--drop` remove as colecoes existentes antes de restaurar. Remova-o se quiser fazer merge dos dados.

### Verificacao pos-restore

```bash
# Conectar ao MongoDB e verificar documentos
docker compose exec mongo mongosh mongodb://mongo:27017/phicube \
  --eval "db.trades.countDocuments()" \
  --quiet
```

---

## Validacao Estrutural de CI (SPEC_041)

Workflow: `.github/workflows/spec041-validation.yml`

Objetivo: bloquear PRs com erro estrutural em configuracao, arquitetura e
seguranca antes do merge.

Validadores:

- `python tools/validate_env_example.py`
  - ERROR: campo obrigatorio de `Settings` ausente no `.env.example`
  - WARNING: variavel no `.env.example` sem correspondencia em `Settings`
- `python tools/validate_spec_freshness.py --base-dir docs/SDD --max-age 90`
  - ERROR: SPEC em rascunho stale acima da janela
  - WARNING: SPEC concluida stale acima da janela
- `python tools/validate_layers.py --src-dir src`
  - ERROR: import entre camadas fora da matriz permitida

Seguranca:

- Scanner de segredos no diff via TruffleHog no workflow `spec041-validation`.

Execucao local recomendada:

```bash
python tools/validate_env_example.py
python tools/validate_spec_freshness.py --base-dir docs/SDD --max-age 90
python tools/validate_layers.py --src-dir src
pytest tests/tools/ -v
```
