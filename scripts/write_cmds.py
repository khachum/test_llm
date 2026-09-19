#!/usr/bin/env python3
"""Сохранение точных команд запуска для каждой конфигурации и каждого прогона.

usage: write_cmds.py <plan.json>

Пишет в <outdir>/cmd/:
  <config>_serve.sh        — полная команда vllm serve со всеми флагами и переменными
  <config>_<prof>_c<N>_bench.sh — полная команда vllm bench serve для прогона
"""
import json, sys
from pathlib import Path

SERVE_TMPL = """#!/bin/bash
# {comment}
# Конфигурация {name}: TP={tp}, DP={dp}, карт={cards}
source /data/scripts/env.sh
export ASCEND_RT_VISIBLE_DEVICES={devices}
export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
export HCCL_BUFFSIZE=512
export HCCL_OP_EXPANSION_MODE=AIV
vllm serve {model_dir} \\
    --host 127.0.0.1 --port {port} \\
    --served-model-name bench \\
    --tensor-parallel-size {tp} \\
    --data-parallel-size {dp} \\
    --max-model-len {mml} \\
    --gpu-memory-utilization 0.9 \\
    --trust-remote-code
"""

BENCH_TMPL = """#!/bin/bash
# Прогон {tag}: профиль {prof} ({inp}->{out} токенов), concurrency={conc}
source /data/scripts/env.sh
vllm bench serve \\
    --backend vllm \\
    --host 127.0.0.1 --port {port} \\
    --model {model_dir} \\
    --served-model-name bench \\
    --dataset-name random \\
    --random-input-len {inp} \\
    --random-output-len {out} \\
    --num-prompts {nprompts} \\
    --max-concurrency {conc} \\
    --ignore-eos \\
    --percentile-metrics ttft,tpot,itl,e2el \\
    --metric-percentiles 50,99 \\
    --seed 1234 \\
    --save-result --result-dir {outdir}/logs --result-filename {tag}.json
"""


def write_for_plan(plan_path):
    plan = json.loads(Path(plan_path).read_text())
    profiles = {p["code"]: p for p in plan["profiles"]}
    written = 0
    for cfg in plan["configs"]:
        outdir = Path(cfg["outdir"])
        cmddir = outdir / "cmd"
        cmddir.mkdir(parents=True, exist_ok=True)
        cards = cfg["tp"] * cfg["dp"]
        (cmddir / f"{cfg['name']}_serve.sh").write_text(SERVE_TMPL.format(
            comment=cfg.get("comment", ""), name=cfg["name"], tp=cfg["tp"], dp=cfg["dp"],
            cards=cards, devices=",".join(str(i) for i in range(cards)),
            model_dir=cfg["model_dir"], port=cfg.get("port", 8000), mml=cfg["max_model_len"]))
        written += 1
        for code in cfg["profiles"]:
            prof = profiles[code]
            for conc in cfg["concurrency"]:
                tag = f"{cfg['name']}_{code}_c{conc}"
                (cmddir / f"{tag}_bench.sh").write_text(BENCH_TMPL.format(
                    tag=tag, prof=code, inp=prof["input"], out=prof["output"], conc=conc,
                    nprompts=plan["num_prompts"][str(conc)], port=cfg.get("port", 8000),
                    model_dir=cfg["model_dir"], outdir=cfg["outdir"]))
                written += 1
    print(f"записано файлов команд: {written}")


if __name__ == "__main__":
    write_for_plan(sys.argv[1])
