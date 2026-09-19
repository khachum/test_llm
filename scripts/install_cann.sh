#!/bin/bash
# CANN 9.1.0 (release) в /data/Ascend — версия, валидированная для vllm-ascend 0.23.0.
# В образе стенда стоит CANN 9.1.0-beta.1 с ядрами под 310p: на 910B падает любой оператор.
set -ex
mkdir -p /data/pkgs /data/Ascend
cd /data/pkgs
B="https://ascend-repo.obs.cn-east-2.myhuaweicloud.com/CANN/CANN%209.1.0"
for f in Ascend-cann-toolkit_9.1.0_linux-aarch64.run \
         Ascend-cann-910b-ops_9.1.0_linux-aarch64.run \
         Ascend-cann-nnal_9.1.0_linux-aarch64.run; do
  [ -s $f ] || wget -q --header="Referer: https://www.hiascend.com/" "$B/$f" -O $f
done
chmod +x *.run
unset ASCEND_TOOLKIT_HOME ASCEND_HOME_PATH ASCEND_OPP_PATH ASCEND_AICPU_PATH ATB_HOME_PATH TOOLCHAIN_HOME PYTHONPATH CMAKE_PREFIX_PATH
export LD_LIBRARY_PATH=/usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/driver/lib64/driver
./Ascend-cann-toolkit_9.1.0_linux-aarch64.run  --quiet --install --install-for-all --install-path=/data/Ascend
./Ascend-cann-910b-ops_9.1.0_linux-aarch64.run --quiet --install --install-for-all --install-path=/data/Ascend
source /data/Ascend/ascend-toolkit/set_env.sh
./Ascend-cann-nnal_9.1.0_linux-aarch64.run     --quiet --install --install-for-all --install-path=/data/Ascend
ls /data/Ascend/*/opp/built-in/op_impl/ai_core/tbe/kernel/config/ascend910b/
du -sh /data/Ascend/*
echo CANN_DONE
