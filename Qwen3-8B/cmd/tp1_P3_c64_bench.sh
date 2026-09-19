#!/bin/bash
# Прогон tp1_P3_c64: профиль P3 (256->1024 токенов), concurrency=64
source /data/scripts/env.sh
vllm bench serve \
    --backend vllm \
    --host 127.0.0.1 --port 8000 \
    --model /data/models/Qwen3-8B \
    --served-model-name bench \
    --dataset-name random \
    --random-input-len 256 \
    --random-output-len 1024 \
    --num-prompts 128 \
    --max-concurrency 64 \
    --ignore-eos \
    --percentile-metrics ttft,tpot,itl,e2el \
    --metric-percentiles 50,99 \
    --seed 1234 \
    --save-result --result-dir /data/results/Qwen3-8B/logs --result-filename tp1_P3_c64.json
