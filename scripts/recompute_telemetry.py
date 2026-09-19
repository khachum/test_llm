#!/usr/bin/env python3
"""Пересчёт полей телеметрии в results.csv по активным картам.

Исходный сборщик усреднял утилизацию по всем четырём картам стенда и суммировал
мощность тоже по всем, из-за чего конфигурации на 1-2 картах выглядели недогруженными,
а их мощность завышалась простаивающими картами.

Активной считается карта, на которой занято больше 10 ГБ HBM (то есть загружены веса).

usage: recompute_telemetry.py <results.csv> <logs_root>
  logs_root — каталог, внутри которого лежат <Модель>/logs/telemetry_<тег>.csv
"""
import csv, sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

ACTIVE_HBM_MB = 10_000


def summarize(path):
    rows = list(csv.DictReader(open(path)))
    if not rows:
        return None
    by_card = defaultdict(list)
    for r in rows:
        by_card[int(r["card"])].append(
            (float(r["ts"]), float(r["aicore_pct"]), float(r["power_w"]),
             float(r["hbm_used_mb"]), float(r["hbm_total_mb"])))
    active = [c for c, v in by_card.items() if max(x[3] for x in v) > ACTIVE_HBM_MB]
    if not active:
        active = list(by_card)
    util = [x[1] for c in active for x in by_card[c]]
    hbm = [100.0 * x[3] / x[4] for c in active for x in by_card[c]]
    # мощность: суммируем по активным картам в каждый момент, затем усредняем по времени
    per_ts = defaultdict(float)
    for c in active:
        for ts, _, pw, _, _ in by_card[c]:
            per_ts[round(ts, 1)] += pw
    return {
        "cards_active": len(active),
        "npu_util_avg_pct": round(mean(util), 1),
        "npu_util_max_pct": round(max(util), 1),
        "power_avg_w": round(mean(per_ts.values()), 1),
        "hbm_max_pct": round(max(hbm), 1),
    }


def main(csv_path, logs_root):
    csv_path, logs_root = Path(csv_path), Path(logs_root)
    rows = list(csv.DictReader(open(csv_path)))
    fields = list(rows[0].keys())
    patched = 0
    for r in rows:
        if not r.get("profile"):
            continue
        tag = f"{r['config']}_{r['profile']}_c{r['concurrency']}"
        tel = logs_root / r["model"] / "logs" / f"telemetry_{tag}.csv"
        if not tel.exists():
            continue
        s = summarize(tel)
        if not s:
            continue
        s.pop("cards_active", None)
        r.update({k: v for k, v in s.items() if k in fields})
        patched += 1
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"пересчитано строк: {patched}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
