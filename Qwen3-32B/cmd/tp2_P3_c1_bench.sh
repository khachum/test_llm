#!/bin/bash
# Прогон tp2_P3_c1: профиль P3 (256->1024 токенов), concurrency=1
source /data/scripts/env.sh
vllm bench serve \
    --backend vllm \
    --host 127.0.0.1 --port 8000 \
    --model /data/models/Qwen3-32B \
    --served-model-name bench \
    --dataset-name random \
    --random-input-len 256 \
    --random-output-len 1024 \
    --num-prompts 6 \
    --max-concurrency 1 \
    --ignore-eos \
    --percentile-metrics ttft,tpot,itl,e2el \
    --metric-percentiles 50,99 \
    --seed 1234 \
    --save-result --result-dir /data/results/Qwen3-32B/logs --result-filename tp2_P3_c1.json
