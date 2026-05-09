## 1. Planejamento e contrato

- [x] 1.1 Definir função canônica de normalização de símbolo para reconciliação de posição
- [x] 1.2 Definir contrato de confirmação de ausência em 2 ciclos consecutivos

## 2. Implementação

- [x] 2.1 Implementar normalização de símbolo no fluxo `_is_position_open`
- [x] 2.2 Adicionar estado transitório por trade para confirmar ausência em 2 ciclos
- [x] 2.3 Endurecer fluxo `OrderNotFound` com fallback de confirmação robusta antes de manual close
- [x] 2.4 Adicionar telemetria estruturada para reconciliação inconclusiva e manual close confirmado

## 3. Testes

- [x] 3.1 Adicionar teste para equivalência `ATOMUSDT` vs `ATOM/USDT:USDT`
- [x] 3.2 Adicionar teste para bloqueio de manual close em ausência de 1 ciclo
- [x] 3.3 Adicionar teste para autorização de manual close após 2 ciclos consecutivos
- [x] 3.4 Adicionar teste para `OrderNotFound` com posição ainda aberta mantendo trade OPEN

## 4. Validação e fechamento

- [x] 4.1 Rodar `ruff check` e testes do monitor de ordens
- [x] 4.2 Atualizar status da change com evidências e preparar para archive
