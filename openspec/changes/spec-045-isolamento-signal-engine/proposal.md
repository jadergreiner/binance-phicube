## Why

O `SignalEngine` atualmente está acoplado a partes do fluxo operacional, dificultando testes determinísticos e evolução segura das regras de sinal. Este isolamento é necessário agora para reduzir regressões em mudanças de estratégia e acelerar validação em CI.

## What Changes

- Introduzir um boundary explícito para o motor de sinais, separando contrato de entrada/saída da orquestração de runtime.
- Definir interfaces estáveis para avaliação de sinal, contexto de mercado e resultados de decisão.
- Garantir que chamadas ao `SignalEngine` ocorram via adaptador dedicado, com tratamento uniforme de erros e telemetria.
- Cobrir o comportamento isolado com testes unitários focados no contrato, sem dependência de infraestrutura externa.

## Capabilities

### New Capabilities
- `signal-engine-isolation`: Define o contrato isolado do motor de sinais, incluindo entradas, saídas, invariantes e integração por adaptador.

### Modified Capabilities
- Nenhuma.

## Impact

- Código afetado: `src/strategy/`, `src/main.py` (ou módulo de orquestração equivalente), testes em `tests/strategy/` e `tests/` de integração do fluxo.
- APIs: sem mudança de API externa pública; impacto interno no contrato entre estratégia e orquestrador.
- Dependências/sistemas: sem novas dependências obrigatórias; impacto em observabilidade/logs e cobertura de testes.
