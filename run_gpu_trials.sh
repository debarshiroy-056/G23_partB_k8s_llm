#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Simple 5-Trial NEMESIS GPU Runner (Standalone Alternative)
# ─────────────────────────────────────────────────────────────────────────────
# A lightweight alternative to `make -f G23_Makefile_gpu run-nemesis` for
# quickly running 5 back-to-back NEMESIS GPU trials outside of Make.
#
# Workflow:
#   1. Creates results/ if missing.
#   2. Loops 5 times calling G23_custom_scheduler_gpu.py, which picks the
#      best GPU and runs G23_electra_train_gpu.py on it.
#   3. After each run, renames G23_results_gpu.csv to
#      results/G23_results_nemesis_gpu_run<i>.csv so nothing gets overwritten.
#
# Does NOT handle the chaos-GPU process lifecycle - start and stop
# G23_chaos_gpu.py manually if you want a noisy environment for these runs.
# ─────────────────────────────────────────────────────────────────────────────

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
