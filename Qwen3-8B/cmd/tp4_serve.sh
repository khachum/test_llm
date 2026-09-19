#!/bin/bash
# E1: масштабирование по картам, TP=4
# Конфигурация tp4: TP=4, DP=1, карт=4
source /data/scripts/env.sh
export ASCEND_RT_VISIBLE_DEVICES=0,1,2,3
export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
export HCCL_BUFFSIZE=512
export HCCL_OP_EXPANSION_MODE=AIV
vllm serve /data/models/Qwen3-8B \
    --host 127.0.0.1 --port 8000 \
    --served-model-name bench \
    --tensor-parallel-size 4 \
    --data-parallel-size 1 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.9 \
    --trust-remote-code
