#!/bin/bash
# G23_sweep_run.sh

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Phase 1B Network Latency Parameter Sweep Orchestrator
# ─────────────────────────────────────────────────────────────────────────────
# Automates the complete latency sweep experiment across multiple delay
# values. Produces the data that powers both G23_sweep_plot.py and
# G23_phase_plot.py.
#
# Workflow per latency value:
#   1. Applies tc netem delay via G23_netem_apply.sh (or clears for 0ms).
#   2. Runs NUM_TRIALS affinity trials + NUM_TRIALS anti-affinity trials.
#   3. Extracts per-trial CSVs from pod logs using ===CSV_START/END===.
#   4. Stores all output in results_<delay>ms/.
#
# At the end, clears all tc rules and reports total elapsed time.
#
# Overridable via env vars:
#   LATENCIES  - space-separated delay list (default: "0 1 5 10 25")
#   NUM_TRIALS - trials per config per latency (default: 5)
#
# Example: LATENCIES="0 5 15" NUM_TRIALS=3 ./G23_sweep_run.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

LATENCIES=${LATENCIES:-"0 1 5 10 25"}
NUM_TRIALS=${NUM_TRIALS:-5}

echo "══════════════════════════════════════════"
echo "  G23 Latency Sweep"
echo "  Latencies : ${LATENCIES} ms"
echo "  Trials    : ${NUM_TRIALS} per config per latency"
echo "══════════════════════════════════════════"

SWEEP_START=$(date +%s)

for delay in ${LATENCIES}; do
    echo ""
    echo "══════════════════════════════════════════"
    echo "  LATENCY = ${delay}ms"
    echo "══════════════════════════════════════════"

    RESULTS_DIR="results_${delay}ms"
    mkdir -p "${RESULTS_DIR}"

    # Apply latency (or clear if 0)
    if [ "${delay}" -eq 0 ]; then
        echo "── Clearing any existing tc rules (baseline)..."
        bash G23_netem_clear.sh
    else
        echo "── Applying ${delay}ms latency..."
        bash G23_netem_apply.sh "${delay}"
    fi

    # Affinity trials
    for i in $(seq 1 "${NUM_TRIALS}"); do
        echo ""
        echo "── [${delay}ms] Affinity Trial ${i}/${NUM_TRIALS} ──"
        kubectl apply -f G23_k8s_affinity.yaml
        kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/electra-master --timeout=600s
        kubectl logs electra-master | sed -n '/===CSV_START===/,/===CSV_END===/p' | grep -v '===CSV' > "${RESULTS_DIR}/G23_results_affinity_run${i}.csv"
        kubectl delete -f G23_k8s_affinity.yaml
        TOTAL=$(tail -1 "${RESULTS_DIR}/G23_results_affinity_run${i}.csv" | cut -d',' -f3)
        echo "   ✓ Total: ${TOTAL}s"
        sleep 2
    done

    # Anti-Affinity trials
    for i in $(seq 1 "${NUM_TRIALS}"); do
        echo ""
        echo "── [${delay}ms] Anti-Affinity Trial ${i}/${NUM_TRIALS} ──"
        kubectl apply -f G23_k8s_antiaffinity.yaml
        kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/electra-master --timeout=600s
        kubectl logs electra-master | sed -n '/===CSV_START===/,/===CSV_END===/p' | grep -v '===CSV' > "${RESULTS_DIR}/G23_results_antiaffinity_run${i}.csv"
        kubectl delete -f G23_k8s_antiaffinity.yaml
        TOTAL=$(tail -1 "${RESULTS_DIR}/G23_results_antiaffinity_run${i}.csv" | cut -d',' -f3)
        echo "   ✓ Total: ${TOTAL}s"
        sleep 2
    done

    echo ""
    echo "── Completed ${delay}ms (${NUM_TRIALS} affinity + ${NUM_TRIALS} anti-affinity)"
done

# Always clear latency at the end
echo ""
echo "══ Clearing all tc rules..."
bash G23_netem_clear.sh

SWEEP_END=$(date +%s)
ELAPSED=$((SWEEP_END - SWEEP_START))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo "══════════════════════════════════════════"
echo "  Sweep complete!"
echo "  Total time: ${MINUTES}m ${SECONDS}s"
echo ""
echo "  Results directories:"
for delay in ${LATENCIES}; do
    echo "    results_${delay}ms/"
done
echo ""
echo "  Next step:"
echo "    make -f G23_Makefile sweep-summary"
echo "══════════════════════════════════════════"
