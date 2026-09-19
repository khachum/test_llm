#!/bin/bash
# venv с релизной парой vllm 0.23.0 + vllm-ascend 0.23.0 (методика, этап 1, п.4).
# Идемпотентен: повторный запуск доустанавливает недостающее.
set -ex
export PIP_INDEX_URL=https://mirrors.ustc.edu.cn/pypi/simple
export PIP_EXTRA_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple https://download.pytorch.org/whl/cpu/ https://mirrors.huaweicloud.com/ascend/repos/pypi"
export PIP_TRUSTED_HOST="mirrors.ustc.edu.cn pypi.tuna.tsinghua.edu.cn"
export PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=10
source /data/Ascend/ascend-toolkit/set_env.sh
source /data/Ascend/nnal/atb/set_env.sh
[ -x /data/venv-vllm/bin/python ] || /usr/local/python3.12.13/bin/python3 -m venv /data/venv-vllm
source /data/venv-vllm/bin/activate
pip install -U pip wheel setuptools
pip install "vllm==0.23.0"
pip install "vllm-ascend==0.23.0"
pip uninstall -y triton triton-ascend || true
pip install "triton-ascend==3.2.2"
pip install modelscope pandas matplotlib
echo "=== таблица версий (методика, этап 1, п.5)"
pip list | grep -Ei "^(torch|torch-npu|torch_npu|vllm|vllm-ascend|vllm_ascend|triton|triton-ascend|transformers|numpy) "
echo INSTALL_DONE
