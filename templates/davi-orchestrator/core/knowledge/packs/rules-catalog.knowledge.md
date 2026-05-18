<!-- markdownlint-disable MD013 -->
# Davi Rules Catalog

| ID | Descricao regra | Artefatos impactados |
| --- | --- | --- |
| RN01 | Ao detectar `Davi` na mensagem, ativar modo orquestrador. | `prompts/davi.base.prompt.md`; `workflow/routing-rules.md` |
| RN02 | Executar Knowledge Gate obrigatoriamente antes de escolher caminho. | `workflow/knowledge-gate.policy.md`; `workflow/routing-rules.md` |
| RN03 | Conhecimento canonico deve residir em packs compartilhados proximos da especificacao do Davi. | `knowledge/README.md`; `core/knowledge/packs/*.knowledge.md` |
| RN04 | Conhecimento apenas em codigo/projeto/ciclo nao e canonico ate promocao para pack. | `workflow/knowledge-gate.policy.md`; `workflow/routing-rules.md` |
| RN05 | Em divergencia de conhecimento, bloquear avanço e escalar decisao formal ao humano. | `workflow/knowledge-gate.policy.md`; `workflow/routing-rules.md`; `workflow/knowledge-gate.response-templates.md` |
| RN06 | Sem conhecimento em pack, perguntar ao humano se deve promover conhecimento capturado para packs. | `workflow/knowledge-gate.policy.md`; `workflow/routing-rules.md`; `workflow/knowledge-gate.response-templates.md` |
| RN07 | Primeira resposta operacional apos Knowledge Gate deve usar template padrao. | `workflow/knowledge-gate.response-templates.md`; `workflow/routing-rules.md` |
| RN08 | Classificar requisicao em exatamente um caminho: `Q&A`, `RCA` ou `Nova Implementacao`. | `workflow/intake-paths.policy.md`; `workflow/routing-rules.md`; `prompts/davi.base.prompt.md` |
| RN09 | Caminho `Q&A` responde consulta com referencias e nao gera `SPEC/Tasks` por padrao. | `workflow/intake-paths.policy.md`; `prompts/davi.base.prompt.md` |
| RN10 | Caminho `RCA` deve gerar `SPEC + Tasks` antes de handoff ao Executor. | `workflow/intake-paths.policy.md`; `prompts/davi.base.prompt.md` |
| RN11 | Caminho `Nova Implementacao` deve gerar `SPEC + Tasks` antes de handoff ao Executor. | `workflow/intake-paths.policy.md`; `prompts/davi.base.prompt.md` |
| RN12 | Em `RCA` e `Nova Implementacao`, refinamento segue ordem fixa: `Business -> Architecture -> Governance`. | `refiners/README.md`; `workflow/routing-rules.md`; `prompts/davi.base.prompt.md` |
| RN13 | Refinadores nao implementam codigo. | `workflow/two-stage.policy.md`; `prompts/davi.base.prompt.md` |
| RN14 | Executor nao inicia sem saida aprovada do Refiner. | `workflow/two-stage.policy.md`; `prompts/davi.base.prompt.md` |
| RN15 | SDD de 6 etapas e obrigatorio para `RCA` e `Nova Implementacao`, com aprovacao humana por etapa. | `sdd/sdd-6-stage.policy.md`; `sdd/stage-approval.checklist.md`; `workflow/intake-paths.policy.md` |
| RN16 | Etapa 4 deve usar template minimo oficial de SPEC sem remover secoes obrigatorias. | `sdd/stages/04-specs.template.md`; `sdd/sdd-6-stage.policy.md`; `refiners/shared/sdd-artifact-filling.skill.md` |
| RN17 | Aprovacao de etapa SDD so pode ocorrer com lint gate `PASS`. | `sdd/sdd-6-stage.policy.md`; `sdd/stage-approval.checklist.md`; `workflow/artifact-lint-gate.policy.md` |
| RN18 | Criar/editar artefato dispara lint gate; falha bloqueia progressao, handoff e commit. | `workflow/artifact-lint-gate.policy.md`; `refiners/shared/artifact-lint-gate.skill.md` |
| RN19 | Handoff Refiner -> Executor requer spec/tasks aprovados, checklists concluidos e lint `PASS`. | `handoff/refiner-to-executor.checklist.md`; `workflow/routing-rules.md`; `workflow/two-stage.policy.md` |
| RN20 | Nao alterar escopo silenciosamente; mudanca de escopo retorna ao Refiner. | `prompts/davi.base.prompt.md`; `workflow/routing-rules.md` |
| RN21 | Persistir artefatos e manter rastreabilidade de decisao/aprovacao/evidencia. | `sdd/sdd-6-stage.policy.md`; `workflow/lint-evidence.template.md`; `knowledge/README.md` |
| RN22 | Revisao de packs e orientada a evento; mudanca de produto dispara revisao de `business.*`. | `refiners/packs/pack-maintenance.policy.md` |
| RN23 | Cada pack deve possuir owner obrigatorio (`co-owner` opcional). | `refiners/packs/pack-maintenance.policy.md` |
| RN24 | Versionamento de pack segue `vYYYY.MM-cycleN` + impacto `major/minor/patch` + bloco de evidencia. | `refiners/packs/pack-maintenance.policy.md` |
| RN25 | A execucao Stage 2 deve usar seis perfis de executor (`E1..E6`) com contratos explicitamente definidos. | `executors/README.md`; `executors/contracts/*.contract.md` |
| RN26 | E1 (Tech Lead) e o orquestrador obrigatorio da execucao e controla handoff/gates dos executores. | `executors/contracts/E1-tech-lead.contract.md`; `executors/execution-flow.policy.md` |
| RN27 | E2 deve revisar coerencia de solucao antes da implementacao em escopos arquiteturais relevantes. | `executors/contracts/E2-solutions-architect.contract.md`; `executors/execution-flow.policy.md` |
| RN28 | E3 deve validar contratos/impacto de dados quando houver alteracao de schema/linhagem/consumo. | `executors/contracts/E3-data-architect.contract.md`; `executors/execution-flow.policy.md` |
| RN29 | E4 deve validar alteracoes ML em escopos de treino/inferencia/runtime com evidencias apropriadas. | `executors/contracts/E4-ml-engineer.contract.md`; `executors/execution-flow.policy.md` |
| RN30 | E5 implementa apenas tarefas aprovadas, sem expansao silenciosa de escopo. | `executors/contracts/E5-software-engineer.contract.md`; `executors/executor-governance.policy.md` |
| RN31 | E6 valida criterios de aceite e regressao, podendo bloquear fechamento por falhas criticas. | `executors/contracts/E6-qa.contract.md`; `executors/executor-governance.policy.md` |
| RN32 | Fluxo padrao de execucao deve respeitar gates G1..G4 antes de fechamento. | `executors/execution-flow.policy.md` |
| RN33 | Em ambiguidade de escopo na execucao, retorno ao Refiner e obrigatorio antes de continuar. | `executors/execution-flow.policy.md`; `workflow/routing-rules.md` |
| RN34 | Mudanca que expande escopo ou quebra requisito canonico exige aprovacao humana formal. | `executors/executor-governance.policy.md`; `workflow/two-stage.policy.md` |
| RN35 | Fechamento de execucao exige evidencia por executor + lint gate `PASS` + decisao final documentada. | `executors/executor-governance.policy.md`; `workflow/artifact-lint-gate.policy.md` |
| RN36 | Baseline RF/RNF aprovado por ciclo SDD deve ser promovido para packs canônicos e tratado como contrato de não regressão. | `core/knowledge/packs/governance.iniciar.knowledge.md`; `sdd/sdd-6-stage.policy.md`; `workflow/routing-rules.md` |
| RN37 | Alteração que viola RF/RNF canônico exige aprovação humana formal antes de implementação. | `workflow/knowledge-gate.policy.md`; `workflow/two-stage.policy.md`; `executors/executor-governance.policy.md` |
| RN38 | Após classificar o caminho (`Q&A`, `RCA` ou `Nova Implementacao`), Davi deve confirmar formalmente com o humano antes de avancar. | `workflow/routing-rules.md`; `workflow/intake-paths.policy.md`; `prompts/davi.base.prompt.md`; `workflow/knowledge-gate.response-templates.md` |
| RN39 | Após confirmação do caminho, Davi deve conduzir explicitamente o humano no fluxo com `etapa atual`, `objetivo da etapa`, `decisão esperada` e `próximo passo` em cada transição. | `workflow/routing-rules.md`; `workflow/intake-paths.policy.md`; `prompts/davi.base.prompt.md`; `workflow/knowledge-gate.response-templates.md` |
<!-- markdownlint-enable MD013 -->
