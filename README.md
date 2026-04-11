# G23 Part B: Kubernetes-Aware and Hardware-Aware LLM Training Simulation (NEMESIS)

This project benchmarks distributed ML training under different placement strategies and runtime constraints. It compares default placement with a custom multi-objective scheduler named NEMESIS.

The work is organized into four phases:

- Phase 1A (Kubernetes / CPU Baselines + NEMESIS): distributed simulation on a local kind cluster with CPU-noise effects.
- Phase 1B (Kubernetes / Network Latency Sweep): controlled latency injection sweep to compare affinity vs anti-affinity sensitivity.
- Phase 2 (Kubernetes / Topology-Aware): expanded multi-worker kind topology with gang scheduling.
- Phase 3 (Bare-Metal / GPU): host-level GPU placement on a multi-GPU machine using NVIDIA telemetry.

## What This Project Covers

1. Clean baseline: affinity on K8s nodes or execution on clean GPU.
2. Noisy baseline: anti-affinity on K8s nodes or execution on noisy/fragmented GPU.
3. NEMESIS under chaos: dynamic placement based on live telemetry.
4. Latency sweep sensitivity: affinity vs anti-affinity scaling from 0-25ms injected delay.

## NEMESIS Scoring Model

NEMESIS computes a penalty score per candidate target and chooses the minimum.

### Phase 1 (Kubernetes / CPU)

$$
\text{Cost} = (\text{CPU millicores} \times \alpha) + (\text{Latency ms} \times \beta)
$$

Default weights in this phase:

- $\alpha = 1$
- $\beta = 10$

Interpretation: network latency is strongly prioritized.

### Phase 2 (Kubernetes / Topology-Aware)

Phase 2 extends the Kubernetes experiments with topology-aware constraints and gang scheduling on a larger worker topology.

### Phase 3 (Bare-Metal / GPU)

$$
\text{Cost} = (\text{VRAM used GB} \times \alpha) + (\text{GPU utilization \%} \times \beta)
$$

Default weights in this phase:

- $\alpha = 1.0$
- $\beta = 0.5$

Interpretation: lower VRAM pressure is prioritized, then compute utilization.

## Repository Layout

### Shared / Analysis

- `results/`: per-trial CSV outputs.
- `G23_visualizer.py`: Streamlit-based interactive analysis.

### Phase 1: Kubernetes + CPU

- `G23_Dockerfile`: builds `electra-sim:v1`.
- `G23_Makefile`: build, run, plot, and cleanup targets.
- `G23_kind_config.yaml`: kind topology.
- `G23_electra_train.py`: CPU DDP simulation workload.
- `G23_custom_scheduler.py`: K8s watcher + binder scheduler process.
- `G23_network_monitor.py`: node latency monitor.
- `G23_stress_monitor.py`: node CPU metrics monitor.
- `G23_k8s_affinity.yaml`: affinity trial manifest.
- `G23_k8s_antiaffinity.yaml`: anti-affinity trial manifest.
- `G23_k8s_nemesis.yaml`: custom scheduler trial manifest.
- `G23_chaos_cpu.yaml`: CPU stress/noisy-neighbor injector.
- `G23_pipeline.py`: aggregation pipeline for K8s trials.
- `G23_final_plot.py`, `G23_plot_perstep.py`: K8s plot renderers.

### Phase 1B: Kubernetes + Latency Sweep

- `G23_sweep_run.sh`: automated latency sweep runner over multiple delay values.
- `G23_sweep_summary.py`: compiles cross-latency summary CSV.
- `G23_sweep_plot.py`: latency vs total runtime line plot (with error bars).
- `G23_phase_plot.py`: stacked forward/backward/optimizer breakdown across sweep conditions.
- `G23_netem_apply.sh`, `G23_netem_clear.sh`, `G23_netem_status.sh`: netem helpers used by the sweep.

### Phase 2: Kubernetes + Topology-Aware Gang Scheduling

- `G23_topology_config.yaml`: multi-worker kind topology for phase 2.
- `G23_topology_injector.sh`: applies node labels/topology metadata.
- `G23_gang_scheduler.py`: topology-aware gang scheduler.
- `G23_k8s_gang.yaml`: gang scheduling trial manifest.

### Phase 3: Bare-Metal + GPU

- `G23_Makefile_gpu`: GPU trial orchestration and plotting targets.
- `G23_electra_train_gpu.py`: GPU training simulation.
- `G23_custom_scheduler_gpu.py`: host-side GPU selector using NVML stats.
- `G23_chaos_gpu.py`: synthetic GPU stress and fragmentation workload.
- `G23_pipeline_gpu.py`: aggregation pipeline for GPU runs.

## Prerequisites

### For Kubernetes / CPU Phase

- Docker
- kind
- kubectl
- make

### For Bare-Metal / GPU Phase

- Linux machine with at least 2 NVIDIA GPUs
- NVIDIA drivers installed and visible via `nvidia-smi`
- make

### Python Dependencies (Both Phases)

```bash
python3 -m pip install --upgrade pip
python3 -m pip install torch numpy matplotlib kubernetes streamlit pandas plotly nvidia-ml-py
```

## Phase 1A: Kubernetes CPU Workflow

### 1. Create Cluster and Build Image

```bash
kind create cluster --name llm-cluster --config G23_topology_config.yaml
kubectl get nodes -o wide
make -f G23_Makefile setup-cluster
```

### 2. Optional: Enable metrics-server

Recommended if you want `G23_stress_monitor.py` telemetry to be reliable on kind.

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n kube-system patch deployment metrics-server --type='json' -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname"}]'
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s
kubectl top nodes
```

### 3. Run Baselines

```bash
make -f G23_Makefile run-affinity-trials
make -f G23_Makefile run-antiaffinity-trials
```

### 4. Run NEMESIS Under Chaos

Terminal A:

```bash
python G23_custom_scheduler.py
```

Terminal B (optional):

```bash
python G23_network_monitor.py
```

Terminal C (optional):

```bash
python G23_stress_monitor.py
```

Main terminal:

```bash
kubectl apply -f G23_chaos_cpu.yaml
make -f G23_Makefile run-nemesis-trials
kubectl delete -f G23_chaos_cpu.yaml --ignore-not-found
```

### 5. Generate Phase 1 Plots

```bash
make -f G23_Makefile plot
```

Outputs:

- `G23_plot_bar.png`
- `G23_plot_perstep.png`

## Phase 1B: Network Latency Sweep Workflow

This phase runs a parameter sweep over injected inter-node latency and captures per-trial CSVs for affinity and anti-affinity at each delay.

### 1. Run Default Sweep

```bash
make -f G23_Makefile run-latency-sweep
```

Default sweep settings from `G23_sweep_run.sh`:

- `LATENCIES="0 1 5 10 25"`
- `NUM_TRIALS=5` per configuration (affinity + anti-affinity)

### 2. Run Custom Sweep (Optional)

```bash
LATENCIES="0 5 15" NUM_TRIALS=3 ./G23_sweep_run.sh
```

### 3. Generate Sweep Plots and Summary

```bash
make -f G23_Makefile plot
```

If `results_0ms/` exists, this also runs:

- `python G23_sweep_summary.py`
- `python G23_sweep_plot.py`
- `python G23_phase_plot.py`

Phase 1B outputs:

- `G23_sweep_summary.csv`
- `G23_sweep_plot.png`
- `G23_phase_plot.png`
- `results_<latency>ms/` (for each swept latency)

## Phase 2: Topology-Aware Multi-Worker Workflow

### 1. Setup Topology Cluster

```bash
make -f G23_Makefile setup-cluster
kubectl get nodes -o wide
```

### 2. Run All Phase 2 K8s Trial Modes

```bash
make -f G23_Makefile run-affinity-trials
make -f G23_Makefile run-antiaffinity-trials
make -f G23_Makefile run-nemesis-trials
make -f G23_Makefile run-gang-trials
```

### 3. Generate Plots

```bash
make -f G23_Makefile plot
```

### 4. One-Command Full Run

```bash
make -f G23_Makefile all
```

This target runs cluster setup, all K8s trial modes (including phase 2 gang scheduling), plotting, and artifact cleanup.
It includes both Phase 1A and Phase 1B before Phase 2 gang scheduling.

## Phase 3: Bare-Metal GPU Workflow

This phase runs directly on host GPUs and does not require Docker or Kubernetes.

### Main GPU Pipeline Commands

```bash
make -f G23_Makefile_gpu all
make -f G23_Makefile_gpu plot
```

What they do:

- `all`: runs clean, noisy, and NEMESIS GPU trials; manages chaos process lifecycle.
- `plot`: regenerates GPU aggregate plots from `results/` CSV files.

GPU outputs:

- `G23_plot_bar_gpu.png`
- `G23_plot_perstep_gpu.png`

## Optional Validation

Quick K8s scheduler interception check:

```bash
python G23_custom_scheduler.py
kubectl apply -f G23_test_pod.yaml
```

Interactive analysis UI:

```bash
streamlit run G23_visualizer.py
```

## Troubleshooting

- `kubectl top nodes` fails or stress monitor returns 404:
  Install metrics-server and wait for rollout completion.
- NEMESIS pods stay Pending in K8s phase:
  Keep `G23_custom_scheduler.py` running and verify `schedulerName: nemesis` in manifest.
- GPU telemetry import/deprecation warnings:
  Use `nvidia-ml-py` package and remove deprecated standalone `pynvml` package if present.
- Missing or stale plots:
  Confirm expected CSVs exist in `results/`, then rerun plot target.

## Cleanup

### Kubernetes/CPU artifacts

```bash
make -f G23_Makefile clean
make -f G23_Makefile clean-artifacts
make -f G23_Makefile clean-binaries
make -f G23_Makefile clean-all
```

### Bare-Metal/GPU artifacts

```bash
make -f G23_Makefile_gpu clean
```

## Quick Command Sequences

### Phase 1 quick run

```bash
make -f G23_Makefile setup-cluster
make -f G23_Makefile run-affinity-trials
make -f G23_Makefile run-antiaffinity-trials
# start scheduler separately: python G23_custom_scheduler.py
kubectl apply -f G23_chaos_cpu.yaml
make -f G23_Makefile run-nemesis-trials
kubectl delete -f G23_chaos_cpu.yaml --ignore-not-found
make -f G23_Makefile plot
```

### Phase 2 quick run

```bash
make -f G23_Makefile setup-cluster
make -f G23_Makefile run-gang-trials
make -f G23_Makefile plot
make -f G23_Makefile clean
```

### Phase 1B quick run

```bash
make -f G23_Makefile setup-cluster
make -f G23_Makefile run-latency-sweep
make -f G23_Makefile plot
```

### Phase 3 quick run

```bash
make -f G23_Makefile_gpu all
make -f G23_Makefile_gpu plot
```
