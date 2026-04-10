# G23_pipeline.py
import os
import csv
import glob
import numpy as np

RESULTS_DIR = "results"
NUM_STEPS = 50

def get_totals(config):
    """Reads all CSVs for a given config and extracts the final execution time."""
    pattern = os.path.join(RESULTS_DIR, f"G23_results_{config}_run*.csv")
    files = glob.glob(pattern)
    totals = []
    for f in files:
        with open(f, 'r') as csvfile:
            reader = list(csv.DictReader(csvfile))
            if reader:
                # The cumulative_sec of the final step is the total execution time
                totals.append(float(reader[-1]['cumulative_sec']))
    return totals

# 1. Gather all data
aff_totals = get_totals("affinity")
anti_totals = get_totals("antiaffinity")
nem_totals = get_totals("nemesis")

# 2. Calculate Statistics
def calc_stats(totals):
    if not totals: return 0.0, 0.0
    return float(np.mean(totals)), float(np.std(totals))


def get_step_stats(config):
    """Reads all per-step CSVs for a config and returns mean/std arrays."""
    pattern = os.path.join(RESULTS_DIR, f"G23_results_{config}_run*.csv")
    files = sorted(glob.glob(pattern))
    runs = []

    for file_path in files:
        with open(file_path, "r", newline="") as csvfile:
            reader = list(csv.DictReader(csvfile))
            if not reader:
                continue

            step_times = []
            for row in reader:
                if "step_time_sec" not in row:
                    continue
                step_times.append(float(row["step_time_sec"]))

            if len(step_times) >= NUM_STEPS:
                runs.append(step_times[:NUM_STEPS])

    if not runs:
        zeros = [0.0] * NUM_STEPS
        return zeros, zeros, 0

    arr = np.array(runs, dtype=float)
    return arr.mean(axis=0).tolist(), arr.std(axis=0).tolist(), arr.shape[0]

aff_mean, aff_std = calc_stats(aff_totals)
anti_mean, anti_std = calc_stats(anti_totals)
nem_mean, nem_std = calc_stats(nem_totals)

aff_step_mean, aff_step_std, aff_step_n = get_step_stats("affinity")
anti_step_mean, anti_step_std, anti_step_n = get_step_stats("antiaffinity")
nem_step_mean, nem_step_std, nem_step_n = get_step_stats("nemesis")

experiments = ['Baseline\n(Affinity)', 'Baseline\n(Anti-Affinity)', 'NEMESIS\n(Chaos Mode)']
means = [aff_mean, anti_mean, nem_mean]
stds = [aff_std, anti_std, nem_std]

# 3. Generate the strictly HARDCODED plotting script
plot_script = f"""# G23_final_plot.py
import matplotlib.pyplot as plt

# HARDCODED VALUES TO STRICTLY SATISFY RULE #4
experiments = {experiments}
means = {means}
stds = {stds}

plt.figure(figsize=(10, 6))
bars = plt.bar(experiments, means, yerr=stds, capsize=8, color=['#4C72B0', '#DD8452', '#55A868'], edgecolor='black')
plt.ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
plt.title('Phase 2: NEMESIS vs Default Kubernetes (n=5 trials)', fontsize=14, fontweight='bold')

# Add values with standard deviation on top of bars
for bar, mean, std in zip(bars, means, stds):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.5, 
             f'{{mean:.2f}}s ± {{std:.2f}}s', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig('G23_plot_bar.png', dpi=300)
print("📊 Plot successfully generated as G23_plot_bar.png")
"""

with open('G23_final_plot.py', 'w') as f:
    f.write(plot_script)

perstep_script = f"""# G23_plot_perstep.py
import matplotlib.pyplot as plt
import numpy as np

# HARDCODED VALUES TO STRICTLY SATISFY THE SUBMISSION RULE
steps = np.arange({NUM_STEPS})
aff_mean = np.array({aff_step_mean})
aff_std = np.array({aff_step_std})
anti_mean = np.array({anti_step_mean})
anti_std = np.array({anti_step_std})
nem_mean = np.array({nem_step_mean})
nem_std = np.array({nem_step_std})

def plot_series(steps, mean_vals, std_vals, label, color):
    plt.plot(steps, mean_vals, label=label, color=color, linewidth=2)
    plt.fill_between(steps, mean_vals - std_vals, mean_vals + std_vals, color=color, alpha=0.15)

plt.figure(figsize=(12, 6))
plot_series(steps, aff_mean, aff_std, "Affinity (n={aff_step_n})", "#2CA02C")
plot_series(steps, anti_mean, anti_std, "Anti-Affinity (n={anti_step_n})", "#D62728")
plot_series(steps, nem_mean, nem_std, "NEMESIS (n={nem_step_n})", "#1F77B4")

plt.grid(True, linestyle="--", alpha=0.7)
plt.xlabel("Training Step", fontweight="bold")
plt.ylabel("Step Latency (seconds)", fontweight="bold")
plt.title("G23: Per-Step Latency Comparison (mean ± 1σ)", fontsize=14, fontweight="bold")
plt.xlim(-1, len(steps))
plt.legend(fontsize=10, loc="upper right", framealpha=1.0, edgecolor="darkgray")

plt.tight_layout()
plt.savefig("G23_plot_perstep.png", dpi=300)
print("📈 Per-step latency plot successfully generated as G23_plot_perstep.png")
"""

with open('G23_plot_perstep.py', 'w') as f:
    f.write(perstep_script)

print("✅ Pipeline complete! Hardcoded G23_final_plot.py and G23_plot_perstep.py have been generated from the raw CSV data.")