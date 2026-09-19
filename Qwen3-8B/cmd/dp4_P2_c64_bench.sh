#!/bin/bash
# Прогон dp4_P2_c64: профиль P2 (2048->128 токенов), concurrency=64
source /data/scripts/env.sh
vllm bench serve \
    --backend vllm \
    --host 127.0.0.1 --port 8000 \
    --model /data/models/Qwen3-8B \
    --served-model-name bench \
    --dataset-name random \
    --random-input-len 2048 \
    --random-output-len 128 \
    --num-prompts 128 \
    --max-concurrency 64 \
    --ignore-eos \
    --percentile-metrics ttft,tpot,itl,e2el \
    --metric-percentiles 50,99 \
    --seed 1234 \
    --save-result --result-dir /data/results/Qwen3-8B/logs --result-filename dp4_P2_c64.json
