# Binance Phicube

> *"Operar com disciplina é transformar método em resultado. Automatizar é garantir que a disciplina não falhe."*

**Binance Phicube** é um sistema de *auto trade* para a corretora **Binance** que aplica de forma automática e disciplinada a estratégia **BO Williams — Phicube**, eliminando o componente emocional das decisões de entrada e saída no mercado de criptoativos.

**Natureza:** ferramenta de uso pessoal (instância única), com um único conjunto de credenciais do operador. Não é uma plataforma multi-usuário.

---

## 📚 Documentação

| Documento | Descrição |
|-----------|-----------|
| [MANIFESTO.md](./MANIFESTO.md) | Conceito de negócio, propósito, visão, missão e princípios fundadores |
| [PRD.md](./PRD.md) | Requisitos de produto (o quê e por quê) |
| [docs/SDD/SPEC.md](./docs/SDD/SPEC.md) | Especificação técnica (como implementar) |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Como contribuir com o projeto |
| [AGENTS.md](./AGENTS.md) | Guia durável para agentes (execução, validação e critérios de pronto) |
| [code_review.md](./code_review.md) | Checklist padrão de revisão técnica |
| [PLANS.md](./PLANS.md) | Template de plano para tarefas complexas |
| [docs/CODEX_TASK_TEMPLATE.md](./docs/CODEX_TASK_TEMPLATE.md) | Template de pedido para reduzir retrabalho com Codex |
| [docs/CODEX_BEST_PRACTICES_ADOPTION.md](./docs/CODEX_BEST_PRACTICES_ADOPTION.md) | Adoção local das boas práticas oficiais do Codex |
| [docs/SKILLS_ADOPTION_PLAYBOOK.md](./docs/SKILLS_ADOPTION_PLAYBOOK.md) | Playbook de adoção e governança de skills do projeto |
| [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) | Código de conduta da comunidade |
| [LICENSE](./LICENSE) | Licença MIT |

---

## 🎯 Propósito

Automatizar a operação pessoal de criptoativos na Binance Futures USDT-M, aplicando de forma fiel e sistemática a estratégia **BO Williams — Phicube**.

Leia o [MANIFESTO.md](./MANIFESTO.md) para entender o conceito completo do projeto.

---

## ✅ Funcionalidades (escopo)

- Monitoramento contínuo de símbolos selecionados na Binance Futures USDT-M.
- Identificação automática de sinais válidos segundo as regras da estratégia BO Williams Phicube.
- Execução de ordens (entrada, stop loss e take profit) com gestão de risco configurável.
- Registro e relatório de todas as operações para análise de desempenho.

---

## ⚙️ Configuração

> Em breve: instruções de instalação, configuração de variáveis de ambiente e execução do sistema.

### Frontend Canônico

- URL única do dashboard: `http://127.0.0.1:8080/` (servida por `dashboard-api`).
- O runtime oficial utiliza apenas este frontend canônico.
- Smoke automatizado de release: `python tools/smoke_release_frontend_8080.py --canonical-url http://127.0.0.1:8080 --timeframe 15m`.

---

## 🧩 OpenSpec (fluxo oficial)

Este repositório usa o CLI oficial `openspec` como fluxo canônico de governança:

- Inicializar: `openspec init`
- Criar mudança: `openspec new change "<nome-kebab-case>"`
- Explorar mudanças/specs: `openspec list --json`
- Validar mudança: `openspec validate --strict --type change <nome-da-mudanca>`
- Aplicar execução guiada: `/opsx:apply`
- Arquivar mudança: `openspec archive <nome-da-mudanca>`

Política de transição:

- O fluxo compat local (`tools/openspec_local.py`) está **descontinuado** para uso diário.
- Data de corte: **2026-05-15**.

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Leia o [CONTRIBUTING.md](./CONTRIBUTING.md) para saber como participar do projeto.

---

## ⚠️ Aviso Legal

Este projeto é uma **ferramenta de automação** e **não constitui recomendação de investimento**. Operações no mercado de criptoativos envolvem **alto risco**, incluindo a perda total do capital investido. O usuário é o único responsável pelas decisões tomadas e pelos resultados obtidos.

---

## 📄 Licença

Este projeto está licenciado sob a [MIT License](./LICENSE).
