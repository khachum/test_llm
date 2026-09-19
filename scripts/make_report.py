#!/usr/bin/env python3
"""Сборка отчёта по результатам замеров: таблицы + графики на модель.

usage: make_report.py <results.csv> <outdir>

Для каждой модели строит:
  - throughput_<model>.png   — выходной throughput от concurrency по конфигурациям
  - ttft_<model>.png         — медианный TTFT от concurrency (лог. шкала)
  - scaling_<model>.png      — эффективность масштабирования S(n) (методика, E1)
и markdown-таблицы, которые вставляются в README модели.
"""
import csv, sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# пороги интерактивности из методики (раздел 5.3)
TTFT_LIMIT_MS = 2000
TPOT_LIMIT_MS = 50


def load(path):
    rows = []
    for r in csv.DictReader(open(path)):
        if not r.get("profile") or r.get("note", "").startswith("СБОЙ"):
            continue
        for k in ("concurrency", "cards", "tp", "dp", "num_prompts", "completed"):
            r[k] = int(float(r[k])) if r.get(k) else None
        for k in ("ttft_med_ms", "ttft_p99_ms", "tpot_med_ms", "itl_p99_ms",
                  "req_per_s", "out_tok_per_s", "duration_s",
                  "npu_util_avg_pct", "npu_util_max_pct", "power_avg_w", "hbm_max_pct"):
            r[k] = float(r[k]) if r.get(k) else None
        rows.append(r)
    return rows


def line_plot(rows, model, profile, ykey, ylabel, title, outpath, logy=False):
    by_cfg = defaultdict(list)
    for r in rows:
        if r["model"] == model and r["profile"] == profile and r[ykey] is not None:
            by_cfg[r["config"]].append((r["concurrency"], r[ykey]))
    if not by_cfg:
        return False
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for cfg, pts in sorted(by_cfg.items()):
        pts.sort()
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", label=cfg)
    ax.set_xscale("log", base=2)
    if logy:
        ax.set_yscale("log")
    ax.set_xlabel("одновременных запросов (concurrency)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(title="конфигурация")
    fig.tight_layout()
    fig.savefig(outpath, dpi=130)
    plt.close(fig)
    return True


def scaling_plot(rows, model, profile, outpath):
    """S(n) = throughput(n карт) / (n × throughput(база)) — методика, E1."""
    pts = defaultdict(dict)
    for r in rows:
        if r["model"] == model and r["profile"] == profile and r["out_tok_per_s"]:
            pts[r["concurrency"]][r["cards"]] = max(
                pts[r["concurrency"]].get(r["cards"], 0), r["out_tok_per_s"])
    if not pts:
        return False
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for conc in sorted(pts):
        cards = sorted(pts[conc])
        base_n = cards[0]
        base = pts[conc][base_n]
        xs = [c for c in cards]
        ys = [pts[conc][c] / (base * c / base_n) for c in cards]
        ax.plot(xs, ys, marker="o", label=f"concurrency={conc}")
    ax.axhline(1.0, color="gray", ls="--", lw=1)
    ax.set_xlabel("число карт")
    ax.set_ylabel("эффективность масштабирования S(n)")
    ax.set_title(f"{model}, профиль {profile}: масштабирование по картам")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=130)
    plt.close(fig)
    return True


def md_table(rows, model):
    hdr = ("| конфиг | карт | профиль | conc | prompts | TTFT med, мс | TTFT p99, мс | "
           "TPOT med, мс | ITL p99, мс | req/s | вых. ток/с | NPU util avg, % | "
           "мощность, Вт | HBM max, % |")
    sep = "|" + "---|" * 14
    lines = [hdr, sep]
    sel = [r for r in rows if r["model"] == model]
    sel.sort(key=lambda r: (r["config"], r["profile"], r["concurrency"]))
    for r in sel:
        lines.append("| {config} | {cards} | {profile} | {concurrency} | {num_prompts} | "
                     "{ttft_med_ms} | {ttft_p99_ms} | {tpot_med_ms} | {itl_p99_ms} | "
                     "{req_per_s} | {out_tok_per_s} | {npu_util_avg_pct} | "
                     "{power_avg_w} | {hbm_max_pct} |".format(**r))
    return "\n".join(lines)


def saturation(rows, model):
    """Точка насыщения: наибольшая concurrency, где TTFT med <= 2 с и TPOT med <= 50 мс."""
    out = {}
    for r in rows:
        if r["model"] != model or not r["ttft_med_ms"] or not r["tpot_med_ms"]:
            continue
        ok = r["ttft_med_ms"] <= TTFT_LIMIT_MS and r["tpot_med_ms"] <= TPOT_LIMIT_MS
        key = (r["config"], r["profile"])
        if ok:
            out[key] = max(out.get(key, 0), r["concurrency"])
        else:
            out.setdefault(key, 0)
    return out


def main(csv_path, outdir):
    rows = load(csv_path)
    outdir = Path(outdir)
    models = sorted({r["model"] for r in rows})
    for model in models:
        d = outdir / model
        d.mkdir(parents=True, exist_ok=True)
        for prof in sorted({r["profile"] for r in rows if r["model"] == model}):
            line_plot(rows, model, prof, "out_tok_per_s", "выходных токенов/с",
                      f"{model}, профиль {prof}: пропускная способность",
                      d / f"throughput_{prof}.png")
            line_plot(rows, model, prof, "ttft_med_ms", "TTFT медиана, мс",
                      f"{model}, профиль {prof}: задержка до первого токена",
                      d / f"ttft_{prof}.png", logy=True)
        scaling_plot(rows, model, "P1", d / "scaling_P1.png")
        (d / "table.md").write_text(md_table(rows, model) + "\n")
        sat = saturation(rows, model)
        lines = ["| конфиг | профиль | точка насыщения (conc) |", "|---|---|---|"]
        for (cfg, prof), c in sorted(sat.items()):
            lines.append(f"| {cfg} | {prof} | {c if c else 'не достигнута даже при conc=1'} |")
        (d / "saturation.md").write_text("\n".join(lines) + "\n")
        print(f"{model}: графики и таблицы в {d}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
