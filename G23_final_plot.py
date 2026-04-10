# G23_final_plot.py
import matplotlib.pyplot as plt

# HARDCODED VALUES TO STRICTLY SATISFY RULE #4
experiments = ['Baseline\n(Affinity)', 'Baseline\n(Anti-Affinity)', 'NEMESIS\n(Chaos Mode)']
means = [14.283610200000002, 18.4255894, 33.3823618]
stds = [1.0220186672867375, 1.9798037552865284, 2.5601824812251484]

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
