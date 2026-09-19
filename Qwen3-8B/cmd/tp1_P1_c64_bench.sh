#!/bin/bash
# Прогон tp1_P1_c64: профиль P1 (512->512 токенов), concurrency=64
source /data/scripts/env.sh
vllm bench serve \
    --backend vllm \
    --host 127.0.0.1 --port 8000 \
    --model /data/models/Qwen3-8B \
    --served-model-name bench \
    --dataset-name random \
    --random-input-len 512 \
    --random-output-len 512 \
    --num-prompts 128 \
    --max-concurrency 64 \
    --ignore-eos \
    --percentile-metrics ttft,tpot,itl,e2el \
    --metric-percentiles 50,99 \
    --seed 1234 \
    --save-result --result-dir /data/results/Qwen3-8B/logs --result-filename tp1_P1_c64.json
