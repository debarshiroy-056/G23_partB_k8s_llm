# G23_final_plot.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Hardcoded Phase 2 Bar Chart Renderer (Submission Guard)
# ─────────────────────────────────────────────────────────────────────────────
# A reproducibility-safe version of the Phase 2 bar chart that uses frozen
# numeric values instead of re-reading CSVs. Ensures the plot in the report
# matches the exact numbers cited even if `results/` is wiped or the
# environment is not available at submission time.
#
# Renders: G23_plot_bar.png showing mean ± std across 5 trials for
# Affinity / Anti-Affinity / NEMESIS (Chaos Mode) configurations.
# ─────────────────────────────────────────────────────────────────────────────

import matplotlib.pyplot as plt

# HARDCODED VALUES TO STRICTLY SATISFY RULE #4
experiments = ['Baseline\n(Affinity)', 'Baseline\n(Anti-Affinity)', 'NEMESIS\n(Chaos Mode)']
means = [18.176344, 20.0959492, 36.1185596]
stds = [1.0718180685898142, 0.5072084141468474, 3.765985029055565]

plt.figure(figsize=(10, 6))
bars = plt.bar(experiments, means, yerr=stds, capsize=8, color=['#4C72B0', '#DD8452', '#55A868'], edgecolor='black')
plt.ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
plt.title('Phase 2: NEMESIS vs Default Kubernetes (n=5 trials)', fontsize=14, fontweight='bold')

# Add values with standard deviation on top of bars
for bar, mean, std in zip(bars, means, stds):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.5, 
             f'{mean:.2f}s ± {std:.2f}s', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig('G23_plot_bar.png', dpi=300)
print("📊 Plot successfully generated as G23_plot_bar.png")
