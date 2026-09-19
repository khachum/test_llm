#!/usr/bin/env python3
"""Оркестратор серии замеров vLLM-Ascend (методика lab-ascend-910b.md, этап 3).

Для каждой конфигурации: поднимает сервер, прогревает, гоняет профили нагрузки
с телеметрией NPU, гасит сервер и дописывает строки в общий CSV.

usage: run_suite.py <plan.json>
"""
import csv, json, os, re, signal, subprocess, sys, time
from pathlib import Path
from statistics import mean

RESULTS = Path("/data/results/results.csv")
FIELDS = [
    "date", "model", "precision", "engine", "config", "tp", "dp", "cards",
    "profile", "input_len", "output_len", "source", "concurrency", "num_prompts",
    "ttft_med_ms", "ttft_p99_ms", "tpot_med_ms", "itl_p99_ms",
    "req_per_s", "out_tok_per_s", "completed", "failed", "duration_s",
    "npu_util_avg_pct", "npu_util_max_pct", "power_avg_w", "hbm_max_pct",
    "bench_json", "note",
]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def wait_ready(log_path, proc, timeout=1800):
    """Ждём 'Application startup complete' в логе сервера."""
    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            return False, f"процесс сервера завершился с кодом {proc.returncode}"
        try:
            text = Path(log_path).read_text(errors="ignore")
        except FileNotFoundError:
            text = ""
        if "Application startup complete" in text:
            return True, None
        time.sleep(5)
    return False, f"сервер не поднялся за {timeout} с"


def stop_server(proc):
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGTERM)
    for _ in range(60):
        if proc.poll() is not None:
            return
        time.sleep(2)
    proc.kill()
    proc.wait(timeout=60)


def npu_free(timeout=180):
    """Ждём, пока карты освободятся (методика, раздел 10)."""
    start = time.time()
    while time.time() - start < timeout:
        out = subprocess.run(["npu-smi", "info"], capture_output=True, text=True).stdout
        if out.count("No running processes found") >= 1 and "VLLM" not in out:
            return True
        time.sleep(5)
    return False


def telemetry_summary(path):
    """avg/max утилизации, средняя мощность на карту, максимум занятой HBM."""
    try:
        rows = list(csv.DictReader(open(path)))
    except Exception:
        return {}
    if not rows:
        return {}
    util = [float(r["aicore_pct"]) for r in rows]
    power = [float(r["power_w"]) for r in rows]
    hbm = [100.0 * float(r["hbm_used_mb"]) / float(r["hbm_total_mb"]) for r in rows]
    cards = len({r["card"] for r in rows})
    return {
        "npu_util_avg_pct": round(mean(util), 1),
        "npu_util_max_pct": round(max(util), 1),
        # мощность суммируем по картам: среднее по времени от суммы карт
        "power_avg_w": round(mean(power) * cards, 1),
        "hbm_max_pct": round(max(hbm), 1),
    }


def run_bench(cfg, prof, conc, nprompts, port, outdir, tag, warmup=False):
    result_name = f"{tag}.json"
    cmd = [
        "vllm", "bench", "serve",
        "--backend", "vllm",
        "--host", "127.0.0.1", "--port", str(port),
        "--model", cfg["model_dir"],
        "--served-model-name", "bench",
        "--dataset-name", "random",
        "--random-input-len", str(prof["input"]),
        "--random-output-len", str(prof["output"]),
        "--num-prompts", str(nprompts),
        "--max-concurrency", str(conc),
        "--ignore-eos",
        "--percentile-metrics", "ttft,tpot,itl,e2el",
        "--metric-percentiles", "50,99",
        "--seed", "1234",
    ]
    if not warmup:
        cmd += ["--save-result", "--result-dir", str(outdir), "--result-filename", result_name]
    log_path = Path(outdir) / f"{tag}.log"
    with open(log_path, "w") as lf:
        r = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, text=True)
    return r.returncode, Path(outdir) / result_name, log_path


def main(plan_path):
    plan = json.loads(Path(plan_path).read_text())
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    new_file = not RESULTS.exists()
    csvf = open(RESULTS, "a", newline="")
    writer = csv.DictWriter(csvf, fieldnames=FIELDS)
    if new_file:
        writer.writeheader()
        csvf.flush()

    for cfg in plan["configs"]:
        outdir = Path(cfg["outdir"])
        (outdir / "logs").mkdir(parents=True, exist_ok=True)
        (outdir / "cmd").mkdir(parents=True, exist_ok=True)
        port = cfg.get("port", 8000)
        serve_log = outdir / "logs" / f"serve_{cfg['name']}.log"

        serve_cmd = [
            "/data/scripts/serve_cfg.sh", cfg["model_dir"], str(cfg["tp"]), str(cfg["dp"]),
            str(port), str(cfg["max_model_len"]),
        ] + cfg.get("extra", [])
        # сохраняем точную команду запуска рядом с логами (требование методики)
        (outdir / "cmd" / f"{cfg['name']}.sh").write_text(
            "#!/bin/bash\n# " + cfg.get("comment", "") + "\n" + " ".join(serve_cmd) + "\n")

        log(f"=== конфигурация {cfg['name']}: TP={cfg['tp']} DP={cfg['dp']} карт={cfg['tp']*cfg['dp']}")
        with open(serve_log, "w") as sl:
            proc = subprocess.Popen(serve_cmd, stdout=sl, stderr=subprocess.STDOUT,
                                    start_new_session=True)
        ok, err = wait_ready(serve_log, proc)
        if not ok:
            log(f"!!! сервер {cfg['name']} не поднялся: {err}")
            stop_server(proc)
            npu_free()
            writer.writerow({
                "date": time.strftime("%Y-%m-%d"), "model": cfg["model"], "precision": cfg["precision"],
                "engine": plan["engine"], "config": cfg["name"], "tp": cfg["tp"], "dp": cfg["dp"],
                "cards": cfg["tp"] * cfg["dp"], "note": f"СБОЙ: {err}",
            })
            csvf.flush()
            continue
        log(f"сервер {cfg['name']} готов")

        try:
            # прогрев: первый прогон серии в таблицу не идёт (методика, 5.3)
            wp = plan["profiles"][0]
            log("прогрев")
            run_bench(cfg, wp, 4, 8, port, outdir / "logs", f"warmup_{cfg['name']}", warmup=True)

            for prof in [p for p in plan["profiles"] if p["code"] in cfg["profiles"]]:
                for conc in cfg["concurrency"]:
                    nprompts = plan["num_prompts"][str(conc)]
                    tag = f"{cfg['name']}_{prof['code']}_c{conc}"
                    log(f"прогон {tag}: {prof['input']}->{prof['output']}, "
                        f"concurrency={conc}, prompts={nprompts}")
                    tel_csv = outdir / "logs" / f"telemetry_{tag}.csv"
                    tel = subprocess.Popen(["python3", "/data/scripts/telemetry.py", str(tel_csv)],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    rc, jpath, blog = run_bench(cfg, prof, conc, nprompts, port,
                                                outdir / "logs", tag)
                    tel.terminate()
                    tel.wait(timeout=30)

                    row = {
                        "date": time.strftime("%Y-%m-%d"), "model": cfg["model"],
                        "precision": cfg["precision"], "engine": plan["engine"],
                        "config": cfg["name"], "tp": cfg["tp"], "dp": cfg["dp"],
                        "cards": cfg["tp"] * cfg["dp"], "profile": prof["code"],
                        "input_len": prof["input"], "output_len": prof["output"],
                        "source": "random", "concurrency": conc, "num_prompts": nprompts,
                        "bench_json": str(jpath),
                    }
                    row.update(telemetry_summary(tel_csv))
                    if rc != 0 or not jpath.exists():
                        row["note"] = f"СБОЙ бенчмарка, rc={rc}, см. {blog.name}"
                    else:
                        d = json.loads(jpath.read_text())
                        row.update({
                            "ttft_med_ms": round(d.get("median_ttft_ms", 0), 1),
                            "ttft_p99_ms": round(d.get("p99_ttft_ms", 0), 1),
                            "tpot_med_ms": round(d.get("median_tpot_ms", 0), 1),
                            "itl_p99_ms": round(d.get("p99_itl_ms", 0), 1),
                            "req_per_s": round(d.get("request_throughput", 0), 3),
                            "out_tok_per_s": round(d.get("output_throughput", 0), 1),
                            "completed": d.get("completed"),
                            "failed": nprompts - (d.get("completed") or 0),
                            "duration_s": round(d.get("duration", 0), 1),
                        })
                    writer.writerow(row)
                    csvf.flush()
                    log(f"  -> throughput {row.get('out_tok_per_s')} tok/s, "
                        f"TTFT med {row.get('ttft_med_ms')} мс, TPOT med {row.get('tpot_med_ms')} мс")
        finally:
            log(f"гашу сервер {cfg['name']}")
            stop_server(proc)
            if not npu_free():
                log("!!! карты не освободились, проверить вручную")

    csvf.close()
    log("СЕРИЯ ЗАВЕРШЕНА")


if __name__ == "__main__":
    main(sys.argv[1])
