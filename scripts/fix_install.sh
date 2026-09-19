#!/bin/bash
# Дотягивание triton-ascend: зеркало Huawei рвёт соединение, pip сдаётся, wget -c докачивает.
set -ex
W=triton_ascend-3.2.2-cp312-cp312-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl
U=https://mirrors.huaweicloud.com/ascend/repos/pypi/triton-ascend/$W
wget -c --tries=100 --timeout=30 --waitretry=5 -O /data/pkgs/$W "$U"
ls -la /data/pkgs/$W
source /data/venv-vllm/bin/activate
export PIP_INDEX_URL=https://mirrors.ustc.edu.cn/pypi/simple
export PIP_EXTRA_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
export PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=10
pip uninstall -y triton triton-ascend || true
pip install /data/pkgs/$W
pip install modelscope pandas matplotlib
echo "=== таблица версий (методика, этап 1, п.5)"
pip list | grep -Ei "^(torch|torch-npu|torch_npu|vllm|vllm-ascend|vllm_ascend|triton|triton-ascend|transformers|numpy) "
echo INSTALL_DONE
