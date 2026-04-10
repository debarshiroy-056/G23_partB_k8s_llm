# G23_electra_train_gpu.py
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
