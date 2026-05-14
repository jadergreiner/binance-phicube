/**
 * Tipos TypeScript para API da Phicube Dashboard
 *
 * Corresponde ao contrato da API em /api/v1/
 */

export interface Position {
  symbol: string;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  current_price: number;
  quantity: number;
  pnl_usdt: number;
  pnl_pct: number;
  sl_price: number;
  tp_price: number;
  open_time: string;
  leverage: number;
  margin_usdt: number;
}

export interface PerformanceGlobal {
  total_trades: number;
  win_rate_pct: number;
  total_pnl_usdt: number;
  avg_rrr: number;
  max_drawdown_usdt: number;
  profit_factor: number;
}

export interface PerformanceBySymbol extends PerformanceGlobal {
  symbol: string;
}

export interface PerformanceByTimeframe extends PerformanceGlobal {
  timeframe: string;
}

export interface PerformanceResponse {
  global: PerformanceGlobal;
  by_symbol: PerformanceBySymbol[];
  by_timeframe: PerformanceByTimeframe[];
}

export interface ApiError {
  status: number;
  message: string;
  timestamp: string;
}

export interface HealthStatus {
  status: string;
  uptime_seconds: number;
  mongodb_connected: boolean;
  binance_client_ok: boolean;
  timestamp: string;
}
