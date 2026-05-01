# Conhecimentos Específicos — AppSec

## OWASP Top 10 Aplicado a APIs e Sistemas Financeiros

- A01 Broken Access Control: controle de acesso ao dashboard e APIs internas
- A02 Cryptographic Failures: proteção de API Keys em repouso e em trânsito
- A03 Injection: validação de inputs em parâmetros de configuração e banco de dados
- A05 Security Misconfiguration: revisão de permissões de containers, portas expostas, configurações padrão
- A06 Vulnerable and Outdated Components: análise de dependências Python e imagens Docker
- A09 Security Logging and Monitoring Failures: garantir que eventos de segurança sejam logados

## Segurança de API Keys

- Princípio do menor privilégio: API Keys da Binance devem ter apenas permissões de trading (sem saque)
- Restrição por IP na Binance: configurar IP whitelist para a Key usada em produção
- Rotação periódica de API Keys e processo de revogação em caso de comprometimento
- Auditoria de acesso: monitorar quando e de onde as Keys são usadas

## Segurança de Containers

- Imagens Docker: análise de vulnerabilidades com Trivy ou Snyk
- Usuário não-root nos containers (já implementado — validar e manter)
- Capabilities Linux mínimas: `--cap-drop=ALL` onde aplicável
- Volumes com permissões mínimas
- Network: containers sem portas expostas desnecessariamente ao host ou à internet

## Gerenciamento de Segredos

- Variáveis de ambiente como método mínimo aceitável (nunca hardcoded no código)
- Docker secrets ou Vault como próximo nível de maturidade
- `.env` nunca commitado no repositório (validar `.gitignore`)
- Pre-commit hooks para detectar segredos no código (gitleaks, detect-secrets)

## Análise de Dependências

- pip-audit ou Safety para identificar vulnerabilidades conhecidas nas dependências Python
- Trivy para scan de imagens Docker no pipeline de CI
- Revisão periódica de dependências: atualizações de segurança em ccxt, motor, pydantic
