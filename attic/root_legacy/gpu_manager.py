import torch
from pynvml import (
    nvmlInit,
    nvmlDeviceGetHandleByIndex,
    nvmlDeviceGetMemoryInfo,
)

nvmlInit()

DEFAULT_GPU_INDEX = 0
DEFAULT_THRESHOLD_MB = 2100

def get_free_gpu_mem_mb(idx=DEFAULT_GPU_INDEX):
    handle = nvmlDeviceGetHandleByIndex(idx)
    info = nvmlDeviceGetMemoryInfo(handle)
    return info.free / (1024 * 1024)

def can_use_gpu(threshold_mb=DEFAULT_THRESHOLD_MB):
    if not torch.cuda.is_available():
        return False
    free_mb = get_free_gpu_mem_mb()
    print(f"[GPU Manager] Free GPU memory: {free_mb:.2f} MB (Threshold: {threshold_mb} MB)")
    return free_mb > threshold_mb

def auto_select_device(threshold_mb=DEFAULT_THRESHOLD_MB):
    device = "cuda" if can_use_gpu(threshold_mb) else "cpu"
    print(f"[GPU Manager] Selected device: {device}")
    return device
