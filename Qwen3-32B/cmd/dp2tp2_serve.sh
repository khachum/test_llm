#!/bin/bash
# две реплики по TP=2: 4 карты, сравнение с TP=4
# Конфигурация dp2tp2: TP=2, DP=2, карт=4
source /data/scripts/env.sh
export ASCEND_RT_VISIBLE_DEVICES=0,1,2,3
export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
export HCCL_BUFFSIZE=512
export HCCL_OP_EXPANSION_MODE=AIV
vllm serve /data/models/Qwen3-32B \
    --host 127.0.0.1 --port 8000 \
    --served-model-name bench \
    --tensor-parallel-size 2 \
    --data-parallel-size 2 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.9 \
    --trust-remote-code
