# G23_pipeline.py
import os
import csv
import glob
import numpy as np
import matplotlib.pyplot as plt

RESULTS_DIR = "results"
NUM_STEPS = 50

def get_totals(config):
    pattern = os.path.join(RESULTS_DIR, f"G23_results_{config}_run*.csv")
    files = glob.glob(pattern)
    totals = []
    for f in files:
        with open(f, 'r') as csvfile:
            reader = list(csv.DictReader(csvfile))
            if reader:
                totals.append(float(reader[-1]['cumulative_sec']))
    return totals

def get_step_stats(config):
    pattern = os.path.join(RESULTS_DIR, f"G23_results_{config}_run*.csv")
    files = sorted(glob.glob(pattern))
    runs = []
    for file_path in files:
        with open(file_path, "r", newline="") as csvfile:
            reader = list(csv.DictReader(csvfile))
            if reader:
                step_times = [float(row["step_time_sec"]) for row in reader if "step_time_sec" in row]
                if len(step_times) >= NUM_STEPS:
                    runs.append(step_times[:NUM_STEPS])
    if not runs:
        return np.zeros(NUM_STEPS), np.zeros(NUM_STEPS), 0
    arr = np.array(runs, dtype=float)
    return arr.mean(axis=0), arr.std(axis=0), arr.shape[0]

configs = [
    ("affinity", "Baseline\n(Affinity)", "#4C72B0"),
    ("antiaffinity", "Baseline\n(Anti-Affinity)", "#DD8452"),
    ("nemesis", "NEMESIS\n(Chaos Mode)", "#55A868"),
    ("gang", "Topology-Aware\n(Gang Scheduler)", "#9370DB")
]

means, stds, labels, colors = [], [], [], []
for conf, label, color in configs:
    totals = get_totals(conf)
    means.append(np.mean(totals) if totals else 0)
    stds.append(np.std(totals) if totals else 0)
    labels.append(label)
    colors.append(color)

# Generate Bar Plot
plt.figure(figsize=(12, 6))
bars = plt.bar(labels, means, yerr=stds, capsize=8, color=colors, edgecolor='black')
plt.ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
plt.title('Phase 1 & 2: K8s Scheduling vs Topology Bottlenecks (n=5)', fontsize=14, fontweight='bold')

for bar, mean, std in zip(bars, means, stds):
    if mean > 0:
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.5, 
                 f'{mean:.2f}s ± {std:.2f}s', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig('G23_plot_bar.png', dpi=300)

# Generate Per-Step Plot
plt.figure(figsize=(14, 6))
steps = np.arange(NUM_STEPS)
for conf, label, color in configs:
    mean_vals, std_vals, n = get_step_stats(conf)
    if n > 0:
        clean_label = label.replace('\n', ' ')
        plt.plot(steps, mean_vals, label=f"{clean_label} (n={n})", color=color, linewidth=2)
        plt.fill_between(steps, mean_vals - std_vals, mean_vals + std_vals, color=color, alpha=0.15)

plt.grid(True, linestyle="--", alpha=0.7)
plt.xlabel("Training Step", fontweight="bold")
plt.ylabel("Step Latency (seconds)", fontweight="bold")
plt.title("G23: Per-Step Latency Comparison (mean ± 1σ)", fontsize=14, fontweight="bold")
plt.xlim(-1, NUM_STEPS)
plt.legend(fontsize=10, loc="upper right", framealpha=1.0, edgecolor="darkgray")

plt.tight_layout()
plt.savefig('G23_plot_perstep.png', dpi=300)

print("✅ Pipeline complete! G23_plot_bar.png and G23_plot_perstep.png generated.")
