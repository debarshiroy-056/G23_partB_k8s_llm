# G23_custom_scheduler_gpu.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: NEMESIS Bare-Metal GPU Scheduler
# ─────────────────────────────────────────────────────────────────────────────
# Host-level GPU selector that bypasses Kubernetes entirely and talks directly
# to the NVIDIA driver via NVML telemetry to pick the least-fragmented GPU.
#
# How it works:
#   1. Initializes pynvml and iterates over every physical GPU on the host.
#   2. For each GPU, pulls raw hardware metrics:
#        - VRAM used (GB)   via nvmlDeviceGetMemoryInfo
#        - Compute util (%) via nvmlDeviceGetUtilizationRates
#   3. Computes a penalty: Cost = (VRAM_GB * alpha) + (GPU_util * beta)
#      with alpha=1.0, beta=0.5 -> VRAM pressure weighted higher than compute
#      because OOM crashes are catastrophic for LLMs.
#   4. Isolates the training job to the winning GPU by setting
#      CUDA_VISIBLE_DEVICES and launching G23_electra_train_gpu.py.
# ─────────────────────────────────────────────────────────────────────────────

import pynvml
import subprocess
import os

def get_gpu_telemetry():
    """Queries the NVIDIA driver for raw hardware metrics."""
    pynvml.nvmlInit()
    device_count = pynvml.nvmlDeviceGetCount()
    stats = {}
    
    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        
        stats[i] = {
            "vram_used_gb": mem_info.used / (1024 ** 3),
            "gpu_util_percent": utilization.gpu
        }
    
    pynvml.nvmlShutdown()
    return stats

def run_nemesis():
    print("🧠 NEMESIS Multi-Objective GPU Scheduler Activated...")
    stats = get_gpu_telemetry()
    
    best_gpu = None
    lowest_cost = float('inf')
    
    # NEMESIS Algorithm Weights
    alpha = 1.0  # VRAM Weight
    beta = 0.5   # Compute Utilization Weight
    
    print("\n🔍 Evaluating Hardware Pipeline...")
    for gpu_id, metrics in stats.items():
        vram = metrics['vram_used_gb']
        util = metrics['gpu_util_percent']
        
        # The Custom Cost Function
        cost = (vram * alpha) + (util * beta)
        
        warning = " ⚠️ (HIGH LOAD)" if cost > 10 else ""
        print(f"   -> GPU {gpu_id} | VRAM Used: {vram:.2f}GB | Compute: {util}% | Penalty Cost: {cost:.2f}{warning}")
        
        if cost < lowest_cost:
            lowest_cost = cost
            best_gpu = gpu_id
            
    print(f"\n🏆 Selected Target: GPU {best_gpu} (Lowest Penalty)")
    
    # Isolate the job to the winning GPU
    print("Launching PyTorch workload...")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(best_gpu)
    
    subprocess.run(["python", "G23_electra_train_gpu.py"], env=env)

if __name__ == "__main__":
    run_nemesis()
