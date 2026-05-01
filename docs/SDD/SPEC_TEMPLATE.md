# SPEC NNN — [Título Curto da Especificação]

**ID:** SPEC_NNN
**Status:** Rascunho | Em Refinamento | Aprovada | Em Execução | Concluída
**Data:** AAAA-MM-DD
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução)
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`

---

## 1. Objetivo

Descreva em 2–4 frases o que esta SPEC resolve e por que é necessária.
Conecte explicitamente com o PRD.md e/ou SPEC.md (seção impactada).

---

## 2. Escopo

### 2.1 Incluído

- Item 1
- Item 2

### 2.2 Excluído (fora de escopo)

- Item 1 — motivo

---

## 3. Contexto e Referências

| Documento | Seção | Relevância |
|---|---|---|
| `PRD.md` | § N.N | Requisito de origem |
| `docs/SDD/SPEC.md` | § N.N | Contrato técnico impactado |

---

## 4. Regras Funcionais

### RF-NNN-01: [Nome da Regra]

**Descrição:** O que o sistema deve fazer.

**Entradas:**

- `param`: descrição e tipo

**Pré-condições:**

- Condição que deve ser verdadeira antes da execução

**Passos:**

1. Passo 1
2. Passo 2

**Saídas:**

- Retorno esperado com tipo e semântica

**Critério de aceite:**

```text
DADO [contexto]
QUANDO [ação]
ENTÃO [resultado esperado]
```

---

## 5. Invariantes e Contratos

### 5.1 Invariantes de Negócio

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-NNN-01 | Descrição | Ação ao violar |

### 5.2 Contratos de Interface

```python
# Assinatura esperada do método/função
def nome_metodo(param: Tipo) -> RetornoTipo:
    """Docstring resumida."""
```

---

## 6. Testes Requeridos

### 6.1 Testes Unitários

| ID | Descrição | Tipo | Prioridade |
|---|---|---|---|
| TEST_NNN_01 | Cenário feliz | unit | Alta |
| TEST_NNN_02 | Cenário de falha | unit | Alta |

### 6.2 Testes de Integração (Testnet)

| ID | Descrição | Pré-requisito |
|---|---|---|
| INT_NNN_01 | Fluxo completo | Testnet ativa |

---

## 7. Tratamento de Erros

| Erro | Causa | Ação do Sistema |
|---|---|---|
| `ErroTipo` | Descrição | retry / fatal / None |

---

## 8. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Descrição | Alto/Médio/Baixo | Ação de mitigação |

---

## 9. Definição de Pronto (DoD)

- [ ] SPEC aprovada pelo Time A
- [ ] Implementação aderente a todos os contratos desta SPEC
- [ ] `pytest` com 100% das asserções críticas passando
- [ ] Rastreabilidade PRD → SPEC.md → SPEC_NNN → Teste → Código comprovada na PR
- [ ] Nenhuma invariante da seção 5.1 violada em nenhum cenário de teste

---

## 10. Plano de Entrega

1. **Time B lê** `docs/SDD/SPEC.md` (seções impactadas) + esta SPEC_NNN
2. **Time B implementa** na ordem definida nas regras funcionais
3. **Time B valida** com `qa-review` e, se aplicável, `signal-review` / `security-audit`
4. **PR criada** com evidências do DoD
5. **Time A revisa** conformidade antes do merge

---

## Histórico

- **AAAA-MM-DD:** Criação da SPEC_NNN.
