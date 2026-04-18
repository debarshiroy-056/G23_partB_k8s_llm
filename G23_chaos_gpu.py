# G23_chaos_gpu.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Synthetic GPU Chaos Injector
# ─────────────────────────────────────────────────────────────────────────────
# Simulates a real-world "noisy GPU" on multi-tenant hardware by hammering
# GPU 1 with both VRAM fragmentation and sustained compute pressure. Used as
# a background process so that NEMESIS has a clearly sub-optimal GPU to route
# around.
#
# How it works:
#   1. Pins itself to cuda:1 so GPU 0 stays clean.
#   2. Allocates a ~10GB tensor (2500 x 1024 x 1024 float32) to eat VRAM,
#      mimicking a large model already occupying memory.
#   3. Enters an infinite loop doing 4096x4096 matmul operations to saturate
#      the CUDA cores.
#   4. On Ctrl+C, releases VRAM cleanly.
#
# Lifecycle: Started by G23_Makefile_gpu's `setup` target, killed by the
# `stop-chaos` target after all trials complete.
# ─────────────────────────────────────────────────────────────────────────────

import torch
import time

print("😈 Injecting Chaos: Reserving 10GB of VRAM and stressing compute on GPU 1...")

# Force this script to run on GPU 1
device = torch.device("cuda:1")

# Allocate a massive tensor to eat VRAM (~10GB)
vram_hog = torch.empty((2500, 1024, 1024), dtype=torch.float32, device=device)

# Create a small matrix to continuously multiply, simulating compute stress
a = torch.randn(4096, 4096, device=device)
b = torch.randn(4096, 4096, device=device)

try:
    while True:
        # Continuously slam the GPU cores
        c = torch.matmul(a, b)
        time.sleep(0.01)
except KeyboardInterrupt:
    print("\n🛑 Chaos stopped. VRAM released.")
