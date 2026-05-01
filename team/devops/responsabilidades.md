# Responsabilidades — DevOps

## Ambiente de Produção

- Provisionar e manter o servidor de produção (VPS Linux ou cloud) com o sistema rodando 24/7
- Garantir que o `docker compose up` em produção seja idempotente e seguro
- Configurar `restart: unless-stopped` e healthchecks em todos os containers críticos
- Gerenciar backups automáticos do volume MongoDB com retenção de pelo menos 30 dias

## CI/CD

- Implementar pipeline de CI no GitHub Actions:
  - Build da imagem Docker em cada push
  - Execução automática dos testes (`pytest`) em cada PR
  - Deploy automático para produção após merge na branch `main` (com aprovação manual)
- Garantir que o pipeline falhe antes do deploy se os testes não passarem

## Monitoramento e Alertas

- Configurar alertas para os seguintes eventos críticos:
  - Container `phicube-bot` parado ou em loop de restart
  - Container `phicube-mongo` inacessível
  - Uso de CPU/memória acima de 85%
  - Erro de execução de ordens detectado nos logs
- Configurar canal de alerta por Telegram ou e-mail para o Trader Sênior e o Backend Sênior

## Segurança de Infraestrutura

- Garantir que as API Keys da Binance **nunca** sejam expostas em logs, repositório ou variáveis públicas
- Configurar acesso ao servidor apenas por chave SSH, sem acesso root direto
- Renovação automática de certificados SSL
- Manter o servidor com patches de segurança aplicados regularmente

## Colaboração

- Trabalhar com o Backend Sênior para garantir que o `Dockerfile` e o `docker-compose.yml` estejam em produção
- Suportar o time com ambientes de desenvolvimento local via Docker Compose
