# Changelog

## 2026-05-16

- `dashboard-api` `/positions`: clientes devem consumir campos canônicos `quantity` e
  `unrealized_pnl_usdt`.
- Mantidos aliases legados `size` e `unrealized_pnl` por compatibilidade retroativa.
- Adicionada sinalização explícita de depreciação no payload:
  `deprecated_fields.size` e `deprecated_fields.unrealized_pnl`.
- Remoção planejada dos aliases legados na versão `v2` da API.
