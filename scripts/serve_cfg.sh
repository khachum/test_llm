#!/bin/bash
# Запуск сервера vLLM для одной конфигурации стенда.
# usage: serve_cfg.sh <model_dir> <tp> <dp> <port> <max_model_len> [доп. флаги vllm serve...]
set -e
source /data/scripts/env.sh
MODEL=$1; TP=$2; DP=$3; PORT=$4; MML=$5; shift 5
CARDS=$((TP * DP))
export ASCEND_RT_VISIBLE_DEVICES=$(seq -s, 0 $((CARDS - 1)))
export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
export HCCL_BUFFSIZE=512
export HCCL_OP_EXPANSION_MODE=AIV
exec vllm serve "$MODEL" \
    --host 127.0.0.1 --port "$PORT" \
    --served-model-name bench \
    --tensor-parallel-size "$TP" \
    --data-parallel-size "$DP" \
    --max-model-len "$MML" \
    --gpu-memory-utilization 0.9 \
    --trust-remote-code \
    "$@"
