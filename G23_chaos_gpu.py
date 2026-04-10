# G23_chaos_gpu.py
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
