# G23_electra_train_gpu.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Single-GPU ELECTRA Training Simulation
# ─────────────────────────────────────────────────────────────────────────────
# The bare-metal GPU training workload used in Phase 3. Intentionally oversized
# to generate heavy compute and VRAM pressure, so the difference between a
# clean GPU and a fragmented one is clearly measurable.
#
# How it works:
#   1. Auto-detects whichever GPU was assigned via CUDA_VISIBLE_DEVICES (set
#      either manually for baselines, or by G23_custom_scheduler_gpu.py).
#   2. Builds a wide feed-forward network (4096 -> 8192 -> 8192 -> 4096) with
#      a 512x4096 input batch to saturate GPU compute.
#   3. Runs NUM_STEPS=50 iterations; after each step calls
#      torch.cuda.synchronize() to get accurate wall-clock timing instead of
#      the asynchronous dispatch time CUDA normally reports.
#   4. Writes per-step metrics to G23_results_gpu.csv (the Makefile then
#      renames this into results/G23_results_gpu_<config>_run<i>.csv).
# ─────────────────────────────────────────────────────────────────────────────

import os
import csv
import time
import torch
import torch.nn as nn

NUM_STEPS = 50

class DummyModel(nn.Module):
    def __init__(self):
        super().__init__()
        # Made the model extremely wide to generate heavy GPU compute load
        self.net = nn.Sequential(
            nn.Linear(4096, 8192), nn.ReLU(),
            nn.Linear(8192, 8192), nn.ReLU(),
            nn.Linear(8192, 4096)
        )

    def forward(self, x):
        return self.net(x)

def train():
    # Detect the GPU assigned by NEMESIS
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Starting GPU Training Simulation on: {device}")
    
    model = DummyModel().to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    loss_fn = nn.MSELoss()

    # Create dummy data on the GPU
    data = torch.randn(512, 4096, device=device)
    labels = torch.randn(512, 4096, device=device)

    output_csv = "G23_results_gpu.csv"
    step_records = []
    total_start = time.time()

    print("Beginning heavy compute iterations...")
    for step in range(NUM_STEPS):
        step_start = time.time()

        optimizer.zero_grad()
        out = model(data)
        loss = loss_fn(out, labels)
        loss.backward()
        optimizer.step()
        
        # Force CUDA to synchronize so we get accurate timing, not asynchronous dispatch times
        if torch.cuda.is_available():
            torch.cuda.synchronize()

        step_end = time.time()
        step_time = step_end - step_start
        cumulative = step_end - total_start

        step_records.append({
            "step": step,
            "step_time_sec": round(step_time, 6),
            "cumulative_sec": round(cumulative, 6),
            "loss": round(loss.item(), 6),
        })

        if step % 10 == 0:
            print(f"  Step {step}/{NUM_STEPS} | step_time={step_time:.4f}s | cumulative={cumulative:.4f}s")

    total_end = time.time()
    execution_time = total_end - total_start

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["step", "step_time_sec", "cumulative_sec", "loss"])
        writer.writeheader()
        writer.writerows(step_records)

    print(f"\n========================================")
    print(f"  Simulation Complete!")
    print(f"  Total Execution Time : {execution_time:.2f} seconds")
    print(f"========================================\n")

if __name__ == "__main__":
    train()
