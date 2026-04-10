#!/bin/bash
mkdir -p results
echo "🚀 Running 5 NEMESIS GPU Trials..."

for i in {1..5}
do
   echo "── Trial $i/5 ──"
   python G23_custom_scheduler_gpu.py
   
   # Rename the output CSV so it doesn't get overwritten
   mv G23_results_gpu.csv results/G23_results_nemesis_gpu_run${i}.csv
   sleep 1
done

echo "✅ GPU Trials Complete! Files saved to results/ directory."
