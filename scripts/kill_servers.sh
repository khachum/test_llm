#!/bin/bash
me=$$
for p in $(ps -eo pid,args | grep -E "[v]llm serve|[s]erve_cfg.sh" | awk '{print $1}'); do
  [ "$p" = "$me" ] && continue
  kill -TERM "$p" 2>/dev/null
done
for i in $(seq 1 40); do
  ps -eo args | grep -qE "[v]llm serve" || break
  sleep 3
done
echo "серверов осталось: $(ps -eo args | grep -cE '[v]llm serve')"
npu-smi info | grep -cE "No running processes found"
