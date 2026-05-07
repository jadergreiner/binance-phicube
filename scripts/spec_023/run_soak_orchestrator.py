from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pymongo.mongo_client import MongoClient

_DEFAULT_EVIDENCE_PATH = (
    "docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/evidence/soak_evidence.json"
)
_DEFAULT_STABILITY_PATH = "reports/spec023_runtime_stability.json"


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso_utc(raw: str) -> datetime:
    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed.astimezone(UTC)


def _safe_read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def _parse_symbol_triplets(raw: str | None) -> list[str]:
    if not raw:
        return []
    symbols: list[str] = []
    for triplet in raw.split(","):
        t = triplet.strip()
        if not t:
            continue
        parts = t.split(":")
        if parts:
            symbols.append(parts[0].upper())
    return sorted(set(symbols))


def _read_pid_rss_mb(pid: int) -> float | None:
    cmd = ["ps", "-o", "rss=", "-p", str(pid)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    if not out:
        return None
    try:
        rss_kb = int(out.splitlines()[0].strip())
    except ValueError:
        return None
    return round(rss_kb / 1024.0, 4)


def _read_pid_lstart(pid: int) -> str | None:
    cmd = ["ps", "-o", "lstart=", "-p", str(pid)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out if out else None


def _health_check(url: str, timeout_seconds: float = 5.0) -> tuple[bool, int | None, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            status = int(response.status)
            ok = 200 <= status < 300
            return ok, status, None
    except urllib.error.HTTPError as exc:
        return False, int(exc.code), f"http_error:{exc.code}"
    except Exception as exc:  # noqa: BLE001 - operational script should classify all failures
        return False, None, type(exc).__name__


def _collect_runtime_samples(
    *,
    started_at: datetime,
    finished_at: datetime,
    sample_interval_seconds: int,
    pids: list[int],
    health_urls: list[str],
) -> tuple[list[dict], dict[int, int], bool]:
    baseline_start_times = {pid: _read_pid_lstart(pid) for pid in pids}
    restarts = {pid: 0 for pid in pids}
    samples: list[dict] = []
    interrupted = False

    while datetime.now(UTC) < finished_at:
        now = datetime.now(UTC)

        pid_metrics: dict[str, dict[str, float | str | None]] = {}
        for pid in pids:
            current_start = _read_pid_lstart(pid)
            if (
                baseline_start_times.get(pid)
                and current_start
                and current_start != baseline_start_times[pid]
            ):
                restarts[pid] += 1
                baseline_start_times[pid] = current_start
            pid_metrics[str(pid)] = {
                "rss_mb": _read_pid_rss_mb(pid),
                "start_time": current_start,
            }

        health_metrics: dict[str, dict[str, str | int | bool | None]] = {}
        for url in health_urls:
            ok, status_code, error = _health_check(url)
            health_metrics[url] = {
                "ok": ok,
                "status_code": status_code,
                "error": error,
            }

        samples.append(
            {
                "ts": now.isoformat(),
                "elapsed_seconds": round((now - started_at).total_seconds(), 2),
                "pid_metrics": pid_metrics,
                "health_metrics": health_metrics,
            }
        )
        try:
            time.sleep(sample_interval_seconds)
        except KeyboardInterrupt:
            interrupted = True
            break

    return samples, restarts, interrupted


def _build_stability_report(
    *,
    started_at: datetime,
    finished_at: datetime,
    samples: list[dict],
    restarts: dict[int, int],
    memory_growth_threshold_mb: float,
) -> dict:
    pid_summary: dict[str, dict[str, float | int | bool | None]] = {}
    memory_leak_suspected = False
    for pid_str in sorted({k for s in samples for k in s.get("pid_metrics", {}).keys()}):
        rss_values = [
            metrics["rss_mb"]
            for s in samples
            for key, metrics in s.get("pid_metrics", {}).items()
            if key == pid_str and metrics.get("rss_mb") is not None
        ]
        if not rss_values:
            pid_summary[pid_str] = {
                "samples": 0,
                "rss_min_mb": None,
                "rss_max_mb": None,
                "rss_growth_mb": None,
                "restart_count": restarts.get(int(pid_str), 0),
                "memory_leak_suspected": False,
            }
            continue

        rss_growth = float(rss_values[-1]) - float(rss_values[0])
        leak_flag = rss_growth > memory_growth_threshold_mb
        memory_leak_suspected = memory_leak_suspected or leak_flag
        pid_summary[pid_str] = {
            "samples": len(rss_values),
            "rss_min_mb": round(min(float(v) for v in rss_values), 4),
            "rss_max_mb": round(max(float(v) for v in rss_values), 4),
            "rss_growth_mb": round(rss_growth, 4),
            "restart_count": restarts.get(int(pid_str), 0),
            "memory_leak_suspected": leak_flag,
        }

    health_checks = [metrics for s in samples for metrics in s.get("health_metrics", {}).values()]
    total_health = len(health_checks)
    failed_health = sum(1 for h in health_checks if not h.get("ok"))

    restart_total = sum(restarts.values())
    status = "pass"
    reasons: list[str] = []
    if restart_total > 0:
        status = "fail"
        reasons.append(f"process_restart_detected:{restart_total}")
    if failed_health > 0:
        status = "fail"
        reasons.append(f"healthcheck_failures:{failed_health}")
    if memory_leak_suspected:
        status = "fail"
        reasons.append("memory_growth_above_threshold")

    return {
        "status": status,
        "generated_at": _iso_now(),
        "window": {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_hours": round((finished_at - started_at).total_seconds() / 3600.0, 4),
        },
        "thresholds": {
            "memory_growth_threshold_mb": memory_growth_threshold_mb,
            "allowed_restart_count": 0,
            "allowed_health_failures": 0,
        },
        "summary": {
            "sample_count": len(samples),
            "restart_count": restart_total,
            "healthcheck_total": total_health,
            "healthcheck_failures": failed_health,
            "healthcheck_failure_rate": round((failed_health / total_health), 6)
            if total_health
            else 0.0,
            "memory_leak_suspected": memory_leak_suspected,
        },
        "per_pid": pid_summary,
        "fail_reasons": reasons,
    }


def _scan_log_events(log_paths: list[Path], expected_symbols: list[str]) -> dict[str, bool | int]:
    startup_success = False
    shutdown_recorded = False
    health_event = False
    recovery_event = False
    error_event = False
    symbols_seen: set[str] = set()

    for path in log_paths:
        for line in _safe_read_lines(path):
            lower = line.lower()
            if (
                "phicube_starting" in lower
                or "monitor_started" in lower
                or "dashboard_lifecycle_start_success" in lower
            ):
                startup_success = True
            if "heartbeat_recorded" in lower or "health_server_started" in lower:
                health_event = True
            if "shutdown_signal_received" in lower or "phicube_stopped" in lower:
                shutdown_recorded = True
            if "recover" in lower or "retry" in lower:
                recovery_event = True
            if "error" in lower or "failed" in lower:
                error_event = True
            if "monitor_started" in lower:
                for symbol in expected_symbols:
                    if symbol.lower() in lower:
                        symbols_seen.add(symbol)

    monitoring_loop = bool(expected_symbols) and len(symbols_seen) == len(expected_symbols)
    if not expected_symbols:
        monitoring_loop = startup_success

    error_recovery_recorded = recovery_event or not error_event

    return {
        "startup_success": startup_success,
        "monitoring_loop_per_symbol": monitoring_loop,
        "health_event_recorded_in_logs": health_event,
        "error_recovery_events_recorded": error_recovery_recorded,
        "shutdown_recorded": shutdown_recorded,
        "symbols_monitored_count": len(symbols_seen),
        "symbols_expected_count": len(expected_symbols),
    }


def _mongo_heartbeat_count(
    *,
    uri: str,
    database: str,
    started_at: datetime,
    finished_at: datetime,
) -> int:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        collection = client[database]["audit"]
        return int(
            collection.count_documents(
                {
                    "event": "heartbeat",
                    "ts": {"$gte": started_at, "$lte": finished_at},
                }
            )
        )
    except Exception:  # noqa: BLE001 - failing to query mongo should not break artifact generation
        return 0
    finally:
        client.close()


def _load_latest_artifacts(
    *,
    coverage_path: Path,
    order_audit_path: Path,
    stability_path: Path,
) -> list[str]:
    artifacts: list[str] = []
    for path in [
        coverage_path,
        order_audit_path,
        stability_path,
        Path("logs/bot.log"),
        Path("logs/api.log"),
    ]:
        if path.exists():
            artifacts.append(path.as_posix())
    return artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect runtime stability and generate canonical soak_evidence.json."
    )
    parser.add_argument("--duration-hours", type=float, default=48.0)
    parser.add_argument("--sample-interval-seconds", type=int, default=300)
    parser.add_argument("--pid", action="append", type=int, default=[])
    parser.add_argument("--health-url", action="append", default=["http://127.0.0.1:8081"])
    parser.add_argument("--log-file", action="append", default=["logs/bot.log", "logs/api.log"])
    parser.add_argument(
        "--output-evidence",
        default=_DEFAULT_EVIDENCE_PATH,
    )
    parser.add_argument("--output-stability", default=_DEFAULT_STABILITY_PATH)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--started-at",
        default=None,
        help="ISO-8601 UTC timestamp. Required with --skip-collection.",
    )
    parser.add_argument(
        "--finished-at",
        default=None,
        help="ISO-8601 UTC timestamp. Required with --skip-collection.",
    )
    parser.add_argument("--skip-collection", action="store_true")
    parser.add_argument("--memory-growth-threshold-mb", type=float, default=256.0)
    parser.add_argument("--bot-version", default=os.getenv("GIT_SHA", "local-worktree"))
    parser.add_argument("--api-version", default=os.getenv("GIT_SHA", "local-worktree"))
    parser.add_argument(
        "--testnet",
        type=_parse_bool,
        default=_parse_bool(os.getenv("BINANCE_TESTNET", "true")),
    )
    parser.add_argument(
        "--mongo-uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    )
    parser.add_argument("--mongo-database", default=os.getenv("MONGODB_DATABASE", "phicube"))
    parser.add_argument("--symbol-timeframes", default=os.getenv("SYMBOL_TIMEFRAMES"))
    parser.add_argument("--coverage-gate", default="reports/spec023_coverage_gate.json")
    parser.add_argument("--order-audit", default="reports/spec023_order_exec_audit.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.skip_collection:
        if not args.started_at or not args.finished_at:
            print(
                json.dumps(
                    {
                        "status": "fail",
                        "reason": "started_at_and_finished_at_required_when_skip_collection",
                    },
                    indent=2,
                )
            )
            return 1
        started_at = _parse_iso_utc(args.started_at)
        finished_at = _parse_iso_utc(args.finished_at)
        samples: list[dict] = []
        restarts: dict[int, int] = {pid: 0 for pid in args.pid}
        interrupted = False
    else:
        started_at = datetime.now(UTC)
        finished_at = started_at + timedelta(hours=args.duration_hours)
        samples, restarts, interrupted = _collect_runtime_samples(
            started_at=started_at,
            finished_at=finished_at,
            sample_interval_seconds=args.sample_interval_seconds,
            pids=args.pid,
            health_urls=args.health_url,
        )
        finished_at = datetime.now(UTC)

    stability_report = _build_stability_report(
        started_at=started_at,
        finished_at=finished_at,
        samples=samples,
        restarts=restarts,
        memory_growth_threshold_mb=args.memory_growth_threshold_mb,
    )

    expected_symbols = _parse_symbol_triplets(args.symbol_timeframes)
    log_events = _scan_log_events([Path(p) for p in args.log_file], expected_symbols)
    heartbeat_count = _mongo_heartbeat_count(
        uri=args.mongo_uri,
        database=args.mongo_database,
        started_at=started_at,
        finished_at=finished_at,
    )

    mandatory_events = {
        "startup_success": bool(log_events["startup_success"]),
        "monitoring_loop_per_symbol": bool(log_events["monitoring_loop_per_symbol"]),
        "health_checks_recorded": stability_report["summary"]["healthcheck_total"] > 0
        or bool(log_events["health_event_recorded_in_logs"])
        or heartbeat_count > 0,
        "error_recovery_events_recorded": bool(log_events["error_recovery_events_recorded"]),
        "shutdown_recorded": bool(log_events["shutdown_recorded"]),
    }

    duration_hours = round((finished_at - started_at).total_seconds() / 3600.0, 4)
    failures: list[str] = []
    if interrupted:
        failures.append("collection_interrupted")
    if duration_hours < 48.0:
        failures.append(f"duration_hours_below_minimum:{duration_hours}")
    if stability_report["status"] != "pass":
        failures.append("runtime_stability_gate_failed")
    for key, value in mandatory_events.items():
        if value is not True:
            failures.append(f"mandatory_event_missing:{key}")

    result = "approved" if not failures else "reproved"
    failure_reason = "; ".join(failures) if failures else None

    coverage_path = Path(args.coverage_gate)
    order_audit_path = Path(args.order_audit)
    stability_path = Path(args.output_stability)

    evidence = {
        "run_id": args.run_id or f"spec023-soak-{started_at.strftime('%Y%m%d-%H%M%S')}",
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_hours": duration_hours,
        "result": result,
        "failure_reason": failure_reason,
        "environment": {
            "bot_version": args.bot_version,
            "api_version": args.api_version,
            "testnet": bool(args.testnet),
        },
        "mandatory_events": mandatory_events,
        "artifacts": _load_latest_artifacts(
            coverage_path=coverage_path,
            order_audit_path=order_audit_path,
            stability_path=stability_path,
        ),
        "notes": "Gerado automaticamente por scripts/spec_023/run_soak_orchestrator.py.",
        "stability_metrics": stability_report,
        "log_evidence": log_events,
        "heartbeat_count": heartbeat_count,
    }

    stability_output = Path(args.output_stability)
    stability_output.parent.mkdir(parents=True, exist_ok=True)
    stability_output.write_text(json.dumps(stability_report, indent=2), encoding="utf-8")

    evidence_output = Path(args.output_evidence)
    evidence_output.parent.mkdir(parents=True, exist_ok=True)
    evidence_output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print(json.dumps(evidence, indent=2))
    return 0 if result == "approved" else 1


if __name__ == "__main__":
    sys.exit(main())
