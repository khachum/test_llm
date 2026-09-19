#!/usr/bin/env python3
"""Сэмплер телеметрии NPU: раз в 2 с парсит npu-smi info и пишет CSV.
Колонки: ts, card, aicore_pct, power_w, hbm_used_mb, hbm_total_mb.
Останавливается по SIGTERM."""
import csv, re, subprocess, sys, time

# строка 1 карты: | 0     910B1  | OK | 94.1  36  0 / 0 |
RE_HEAD = re.compile(r"^\|\s+(\d+)\s+\S+\s+\|\s+\S+\s+\|\s+([\d.]+)\s+(\d+)\s")
# строка 2 карты: | 0 | 0000:C1:00.0 | 0   0 / 0   3428 / 65536 |
RE_BODY = re.compile(r"^\|\s+\d+\s+\|\s+[0-9A-Fa-f:.]+\s+\|\s+(\d+)\s+\d+\s*/\s*\d+\s+(\d+)\s*/\s*(\d+)")

def sample():
    out = subprocess.run(["npu-smi", "info"], capture_output=True, text=True, timeout=20).stdout
    rows, card, power = [], None, None
    for line in out.splitlines():
        m = RE_HEAD.match(line)
        if m:
            card, power = int(m.group(1)), float(m.group(2))
            continue
        m = RE_BODY.match(line)
        if m and card is not None:
            rows.append((card, int(m.group(1)), power, int(m.group(2)), int(m.group(3))))
            card = None
    return rows

def main(path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "card", "aicore_pct", "power_w", "hbm_used_mb", "hbm_total_mb"])
        while True:
            ts = time.time()
            try:
                for r in sample():
                    w.writerow([f"{ts:.1f}", *r])
                f.flush()
            except Exception as e:                       # телеметрия не должна ронять прогон
                print(f"telemetry error: {e}", file=sys.stderr)
            time.sleep(2)

if __name__ == "__main__":
    main(sys.argv[1])
