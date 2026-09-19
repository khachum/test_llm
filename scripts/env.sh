# Окружение стенда: своя установка CANN 9.1.0 (release) + venv с vllm-ascend 0.23.0.
# В образе стенда CANN 9.1.0-beta.1 собран под 310p, на 910B операторы не работают,
# поэтому переменные заводской установки сначала сбрасываются.
unset ASCEND_TOOLKIT_HOME ASCEND_HOME_PATH ASCEND_OPP_PATH ASCEND_AICPU_PATH ATB_HOME_PATH TOOLCHAIN_HOME PYTHONPATH CMAKE_PREFIX_PATH
export LD_LIBRARY_PATH=/usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/driver/lib64/driver
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
source /data/Ascend/ascend-toolkit/set_env.sh
source /data/Ascend/nnal/atb/set_env.sh
source /data/venv-vllm/bin/activate
export HF_HOME=/data/hf
export HF_ENDPOINT=https://hf-mirror.com
