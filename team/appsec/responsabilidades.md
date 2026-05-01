# Responsabilidades — AppSec

## Auditoria de Segredos e API Keys

- Verificar que as API Keys da Binance **nunca** aparecem em logs, código-fonte, variáveis de ambiente públicas ou histórico do Git
- Validar que o `.gitignore` bloqueia corretamente `.env` e qualquer arquivo com segredos
- Implementar pre-commit hook com `gitleaks` ou `detect-secrets` para bloquear commits com credenciais
- Recomendar configuração de IP whitelist para a API Key de produção na Binance

## Segurança de Dependências

- Executar `pip-audit` (ou Safety) nas dependências do `pyproject.toml` antes de cada release
- Integrar Trivy no pipeline de CI para scan de vulnerabilidades na imagem Docker
- Manter registro das dependências auditadas e das versões aprovadas para produção
- Alertar o Backend Sênior sobre atualizações críticas de segurança em dependências-chave (ccxt, motor, pydantic)

## Hardening de Containers

- Validar que o container `phicube-bot` roda com usuário não-root (já implementado — manter)
- Revisar portas expostas no `docker-compose.yml`: apenas o necessário deve ser acessível externamente
- Garantir que o serviço `mongo-express` esteja disponível **apenas no perfil `dev`** (nunca em produção)
- Recomendar capabilities mínimas para os containers quando viável

## Revisão de Controle de Acesso

- Validar que o dashboard frontend requer autenticação (mesmo que básica no MVP)
- Garantir que a API interna do bot não seja exposta sem autenticação em ambiente de produção
- Revisar as permissões de acesso ao MongoDB: usuário da aplicação não deve ter acesso de admin

## Monitoramento de Segurança

- Garantir que tentativas de acesso não autorizado ao dashboard e ao MongoDB sejam logadas
- Recomendar alertas para eventos suspeitos: múltiplas falhas de autenticação, acesso fora do horário esperado
- Revisar a política de logs: dados sensíveis (keys, saldos detalhados) devem ser mascarados nos logs

## Cadência

- Auditoria completa a cada release maior
- Revisão de dependências mensalmente
- Revisão do `.gitignore` e pre-commit hooks a cada mudança de desenvolvedor no time
