# Conhecimentos Específicos — DevOps

## Containerização

- Docker: multi-stage builds, otimização de imagem, usuário não-root, healthchecks
- Docker Compose: definição de serviços, volumes, networks, depends_on com condições de saúde
- Gerenciamento de secrets em containers: variáveis de ambiente, Docker secrets, arquivos .env

## CI/CD

- GitHub Actions: workflows de build, test e deploy automático
- Estratégias de deploy: rolling update, blue-green, canary
- Gestão de branches e ambientes: dev → staging → produção
- Execução automática de testes unitários e de integração no pipeline

## Infraestrutura e Cloud

- Provisionamento de VPS Linux: Ubuntu/Debian, hardening básico, fail2ban, ufw
- Gerenciamento de DNS, SSL/TLS (Let's Encrypt / Certbot)
- Backup automático de volumes Docker (MongoDB data)
- Desejável: Terraform ou Ansible para infraestrutura como código

## Monitoramento e Alertas

- Prometheus + Grafana: métricas de sistema e aplicação
- Alertmanager: regras de alerta por canal (e-mail, Telegram, Slack)
- Logs centralizados: Loki, ELK Stack ou CloudWatch Logs
- Alertas críticos: bot offline, MongoDB down, memória/CPU críticos, erro de execução de ordens

## Segurança Operacional

- Rotação periódica de API Keys e secrets
- Acesso SSH apenas por chave, sem senha
- Isolamento de rede: containers sem portas expostas desnecessariamente
- Backup criptografado dos dados sensíveis
