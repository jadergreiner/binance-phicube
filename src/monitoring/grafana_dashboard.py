"""
Builder para criação de dashboards Grafana (Builder + Factory Method).

Usa Design Patterns:
- Builder: Constrói dashboard passo a passo
- Factory Method: Cria diferentes tipos de painéis

Exemplo de uso:
    builder = GrafanaDashboardBuilder(title="Phicube Trading Bot")
    builder.with_stat_panel("Posições Abertas", "phicube_positions_open")
    builder.with_graph_panel("Tick Duration", "phicube_tick_duration_seconds_bucket")
    dashboard_json = builder.build()
"""

from __future__ import annotations

import json
from typing import Any


class PanelFactory:
    """
    Factory Method para criar diferentes tipos de painéis Grafana.
    
    Cada método retorna um dict com a estrutura JSON de um painel.
    """

    @staticmethod
    def create_stat_panel(
        title: str,
        metric: str,
        *,
        description: str = "",
        unit: str = "short",
        grid_pos: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """
        Cria um painel do tipo Stat (mostra valor único).
        
        Ideal para: posições abertas, uptime, PnL, contadores totais.
        
        Args:
            title: Título do painel
            metric: Nome da métrica Prometheus
            description: Descrição opcional
            unit: Unidade (short, percent, s, usdt)
            grid_pos: Posição no grid (x, y, w, h)
        """
        if unit == "usdt":
            # Formatação para valores monetários
            expr = f"sum({metric})" if "total" in metric else metric
            value_mapping = {"2": {"text": "USDT", "value": "usdt"}}
        else:
            expr = f"sum({metric})" if "total" in metric else metric
            value_mapping = {}

        return {
            "id": 0,
            "type": "stat",
            "title": title,
            "description": description,
            "gridPos": grid_pos or {"x": 0, "y": 0, "w": 6, "h": 4},
            "fieldConfig": {
                "defaults": {
                    "mappings": value_mapping,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "red", "value": 80},
                        ],
                    },
                    "unit": unit,
                },
                "overrides": [],
            },
            "options": {
                "colorMode": "value",
                "graphMode": "area",
                "justifyMode": "auto",
                "orientation": "auto",
                "reduceOptions": {
                    "calcs": ["lastNotNull"],
                    "fields": "",
                    "values": False,
                },
                "textMode": "auto",
            },
            "targets": [
                {
                    "refId": "A",
                    "expr": expr,
                    "interval": "",
                    "legendFormat": "{{symbol}}",
                }
            ],
        }

    @staticmethod
    def create_graph_panel(
        title: str,
        metric: str,
        *,
        description: str = "",
        unit: str = "s",
        grid_pos: dict[str, int] | None = None,
        legend_format: str = "{{symbol}}",
    ) -> dict[str, Any]:
        """
        Cria um painel do tipo Graph (Time Series).
        
        Ideal para: tick duration, candle latency, sinais ao longo do tempo.
        
        Args:
            title: Título do painel
            metric: Nome da métrica Prometheus (inclui _bucket para histograms)
            description: Descrição opcional
            unit: Unidade (s, ms, percent)
            grid_pos: Posição no grid
            legend_format: Formato da legenda
        """
        # Para histogramas, usa rate
        if "_bucket" in metric:
            expr = f"sum(rate({metric}[5m])) by (le, symbol)"
        else:
            expr = f"sum(rate({metric}[5m])) by (symbol)"

        return {
            "id": 0,
            "type": "timeseries",
            "title": title,
            "description": description,
            "gridPos": grid_pos or {"x": 0, "y": 0, "w": 12, "h": 8},
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "barAlignment": 0,
                        "drawStyle": "line",
                        "fillOpacity": 10,
                        "gradientMode": "none",
                        "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                        "lineInterpolation": "linear",
                        "lineWidth": 1,
                        "pointSize": 5,
                        "scaleDistribution": {"type": "linear"},
                        "showPoints": "auto",
                        "spanNulls": False,
                        "stacking": {"group": "A", "mode": "none"},
                        "thresholdsStyle": {"mode": "off"},
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "red", "value": 80},
                        ],
                    },
                    "unit": unit,
                },
                "overrides": [],
            },
            "options": {
                "legend": {"calcs": [], "displayMode": "list", "showLegend": True},
                "tooltip": {"mode": "single", "sort": "none"},
            },
            "targets": [
                {
                    "refId": "A",
                    "expr": expr,
                    "format": "time_series",
                    "interval": "",
                    "legendFormat": legend_format,
                }
            ],
        }

    @staticmethod
    def create_gauge_panel(
        title: str,
        metric: str,
        *,
        description: str = "",
        max_value: int = 100,
        grid_pos: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """
        Cria um painel do tipo Gauge (mostra valor em um intervalo).
        
        Ideal para: taxa de detecção de sinais, uptime, utilização.
        
        Args:
            title: Título do painel
            metric: Nome da métrica Prometheus
            description: Descrição opcional
            max_value: Valor máximo do gauge
            grid_pos: Posição no grid
        """
        return {
            "id": 0,
            "type": "gauge",
            "title": title,
            "description": description,
            "gridPos": grid_pos or {"x": 0, "y": 0, "w": 6, "h": 6},
            "fieldConfig": {
                "defaults": {
                    "mappings": [],
                    "max": max_value,
                    "min": 0,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "red", "value": 80},
                        ],
                    },
                    "unit": "percent",
                },
                "overrides": [],
            },
            "options": {
                "orientation": "auto",
                "reduceOptions": {
                    "calcs": ["lastNotNull"],
                    "fields": "",
                    "values": False,
                },
                "showThresholdLabels": False,
                "showThresholdMarkers": True,
            },
            "targets": [
                {
                    "refId": "A",
                    "expr": metric,
                    "interval": "",
                    "legendFormat": "",
                }
            ],
        }


class GrafanaDashboardBuilder:
    """
    Builder para construir dashboards Grafana completos.
    
    Usa o padrão Builder para adicionar painéis passo a passo
    e gerar o JSON final do dashboard.
    
    Exemplo:
        builder = GrafanaDashboardBuilder("Phicube Bot")
        builder.with_stat("Posições", "phicube_positions_open")
        builder.with_graph("Tick Duration", "phicube_tick_duration_seconds_bucket")
        json_str = builder.build()
    """

    def __init__(self, title: str = "Phicube Trading Bot") -> None:
        """
        Inicializa o builder com um título.
        
        Args:
            title: Título do dashboard
        """
        self._title = title
        self._panels: list[dict[str, Any]] = []
        self._next_panel_id = 1
        self._next_y = 0

    def with_stat_panel(
        self,
        title: str,
        metric: str,
        *,
        description: str = "",
        unit: str = "short",
        width: int = 6,
        height: int = 4,
    ) -> GrafanaDashboardBuilder:
        """
        Adiciona um painel Stat ao dashboard.
        
        Args:
            title: Título do painel
            metric: Nome da métrica
            description: Descrição opcional
            unit: Unidade (short, percent, s, usdt)
            width: Largura no grid (padrão: 6)
            height: Altura no grid (padrão: 4)
        """
        panel = PanelFactory.create_stat_panel(
            title=title,
            metric=metric,
            description=description,
            unit=unit,
            grid_pos={
                "x": 0,
                "y": self._next_y,
                "w": width,
                "h": height,
            },
        )
        panel["id"] = self._next_panel_id
        self._next_panel_id += 1
        self._next_y += height
        self._panels.append(panel)
        return self

    def with_graph_panel(
        self,
        title: str,
        metric: str,
        *,
        description: str = "",
        unit: str = "s",
        width: int = 12,
        height: int = 8,
        legend_format: str = "{{symbol}}",
    ) -> GrafanaDashboardBuilder:
        """
        Adiciona um painel Graph (Time Series) ao dashboard.
        
        Args:
            title: Título do painel
            metric: Nome da métrica (use _bucket para histogramas)
            description: Descrição opcional
            unit: Unidade
            width: Largura no grid (padrão: 12 - full width)
            height: Altura no grid (padrão: 8)
            legend_format: Formato da legenda
        """
        panel = PanelFactory.create_graph_panel(
            title=title,
            metric=metric,
            description=description,
            unit=unit,
            grid_pos={
                "x": 0,
                "y": self._next_y,
                "w": width,
                "h": height,
            },
            legend_format=legend_format,
        )
        panel["id"] = self._next_panel_id
        self._next_panel_id += 1
        self._next_y += height
        self._panels.append(panel)
        return self

    def with_gauge_panel(
        self,
        title: str,
        metric: str,
        *,
        description: str = "",
        max_value: int = 100,
        width: int = 6,
        height: int = 6,
    ) -> GrafanaDashboardBuilder:
        """
        Adiciona um painel Gauge ao dashboard.
        
        Args:
            title: Título do painel
            metric: Nome da métrica
            description: Descrição opcional
            max_value: Valor máximo
            width: Largura no grid
            height: Altura no grid
        """
        panel = PanelFactory.create_gauge_panel(
            title=title,
            metric=metric,
            description=description,
            max_value=max_value,
            grid_pos={
                "x": 0,
                "y": self._next_y,
                "w": width,
                "h": height,
            },
        )
        panel["id"] = self._next_panel_id
        self._next_panel_id += 1
        self._next_y += height
        self._panels.append(panel)
        return self

    def with_row(self, title: str) -> GrafanaDashboardBuilder:
        """
        Adiciona uma linha (row) para organizar painéis.
        
        Args:
            title: Título da linha
        """
        row = {
            "id": self._next_panel_id,
            "type": "row",
            "title": title,
            "gridPos": {"x": 0, "y": self._next_y, "w": 24, "h": 1},
            "panels": [],
        }
        self._next_panel_id += 1
        self._next_y += 1
        self._panels.append(row)
        return self

    def build(self) -> str:
        """
        Constrói e retorna o JSON do dashboard.
        
        Returns:
            String JSON formatada do dashboard Grafana
        """
        dashboard = {
            "annotations": {
                "list": [
                    {
                        "builtIn": 1,
                        "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                        "enable": True,
                        "hide": True,
                        "iconColor": "rgba(0, 211, 255, 1)",
                        "name": "Annotations & Alerts",
                        "type": "dashboard",
                    }
                ]
            },
            "editable": True,
            "fiscalYearStartMonth": 0,
            "graphTooltip": 0,
            "id": None,
            "links": [],
            "liveNow": False,
            "panels": self._panels,
            "refresh": "5s",
            "schemaVersion": 38,
            "style": "dark",
            "tags": ["phicube", "trading", "binance"],
            "templating": {"list": []},
            "time": {"from": "now-6h", "to": "now"},
            "timepicker": {},
            "timezone": "",
            "title": self._title,
            "uid": "",
            "version": 1,
            "weekStart": "",
        }
        return json.dumps(dashboard, indent=2)


def create_default_dashboard() -> str:
    """
    Factory Method: Cria o dashboard padrão do Phicube.
    
    Este é um Factory Method que usa o Builder para criar
    um dashboard pré-configurado com todas as métricas SPEC_032.
    
    Returns:
        JSON do dashboard padrão
    """
    builder = GrafanaDashboardBuilder("Phicube Trading Bot")

    # Linha: Status Geral
    builder.with_row("Status Geral")
    builder.with_stat_panel(
        "Posições Abertas", "phicube_positions_open", unit="short"
    )
    builder.with_stat_panel(
        "Monitores Ativos", "phicube_monitor_count", unit="short"
    )
    builder.with_stat_panel(
        "Uptime", "time() - phicube_start_time_seconds", unit="s"
    )

    # Linha: Sinais
    builder.with_row("Sinais")
    builder.with_stat_panel(
        "Sinais Detectados", "sum(phicube_signals_total)", unit="short"
    )
    builder.with_stat_panel(
        "Sinais Rejeitados", "sum(phicube_signals_rejected_total)", unit="short"
    )
    builder.with_stat_panel(
        "Avaliações", "sum(phicube_signals_evaluated_total)", unit="short"
    )

    # Linha: Trades e PnL
    builder.with_row("Trades e PnL")
    builder.with_stat_panel(
        "Trades Executados", "sum(phicube_trades_total)", unit="short"
    )
    builder.with_stat_panel(
        "PnL Win Total", "sum(phicube_pnl_realized_win_total)", unit="usdt"
    )
    builder.with_stat_panel(
        "PnL Loss Total", "sum(phicube_pnl_realized_loss_total)", unit="usdt"
    )

    # Linha: Performance
    builder.with_row("Performance")
    builder.with_graph_panel(
        "Tick Duration", "phicube_tick_duration_seconds_bucket", unit="s"
    )
    builder.with_graph_panel(
        "Candle Latency", "phicube_candle_latency_seconds_bucket", unit="s"
    )

    # Linha: Erros e API
    builder.with_row("Erros e API")
    builder.with_stat_panel(
        "Erros Total", "sum(phicube_errors_total)", unit="short"
    )
    builder.with_stat_panel(
        "Requisições API", "sum(phicube_api_requests_total)", unit="short"
    )

    return builder.build()
