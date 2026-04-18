# G23_visualizer.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Interactive NEMESIS Cost Algorithm Visualizer (Streamlit App)
# ─────────────────────────────────────────────────────────────────────────────
# A hands-on educational UI that lets reviewers and teammates tune the
# NEMESIS cost-penalty function and immediately see how the scheduling
# decision changes. Makes the abstract formula tangible.
#
# How it works:
#   1. Exposes alpha (CPU weight) and beta (latency weight) as sliders.
#   2. Exposes two simulated nodes with editable CPU and latency values:
#        - Node 1 represents a "Noisy Neighbor" (high CPU, low latency).
#        - Node 2 represents "Network Lag"      (low CPU, high latency).
#   3. Live-computes Cost = (CPU * alpha) + (Latency * beta) for both and
#      flags the winner (lowest cost).
#   4. Renders two interactive Plotly charts:
#        - A bar chart of current penalty costs for both nodes.
#        - A sensitivity line graph sweeping beta from 1 to 25, showing how
#          the winning node flips as the latency weight is varied.
#
# Launch: `streamlit run G23_visualizer.py`
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import plotly.express as px

# Upgraded to 'wide' layout so the graphs have more room to breathe
st.set_page_config(page_title="NEMESIS Scheduler Visualizer", layout="wide")

st.title("🧠 NEMESIS Cost Algorithm Visualizer")
st.markdown("Adjust the weights and cluster metrics below to see how the NEMESIS Custom Scheduler makes real-time placement decisions.")

# --- SECTION 1: Algorithm Weights ---
st.header("1. Algorithm Tuning (Weights)")
st.write("Formula: `Cost = (CPU * Alpha) + (Latency * Beta)`")
col1, col2 = st.columns(2)
with col1:
    alpha = st.slider("Alpha (CPU Weight)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
with col2:
    beta = st.slider("Beta (Latency Weight)", min_value=1.0, max_value=30.0, value=10.0, step=1.0)

st.divider()

# --- SECTION 2: Node State ---
st.header("2. Live Cluster State")
col3, col4 = st.columns(2)

with col3:
    st.subheader("Node 1: The Noisy Neighbor")
    cpu1 = st.number_input("Node 1 CPU (millicores)", value=4020.0, step=10.0)
    lat1 = st.number_input("Node 1 Latency (ms)", value=2.5, step=0.5)

with col4:
    st.subheader("Node 2: The Network Lag")
    cpu2 = st.number_input("Node 2 CPU (millicores)", value=17.0, step=1.0)
    lat2 = st.number_input("Node 2 Latency (ms)", value=100.9, step=1.0)

st.divider()

# --- SECTION 3: The Brain's Decision ---
st.header("3. Scheduling Decision")

# Calculate Current Costs
cost1 = (cpu1 * alpha) + (lat1 * beta)
cost2 = (cpu2 * alpha) + (lat2 * beta)

# Display Results visually at the top
res1, res2 = st.columns(2)
with res1:
    if cost1 <= cost2:
        st.success(f"🏆 WINNER: Node 1 (Cost: {cost1:.2f})")
    else:
        st.error(f"❌ LOSER: Node 1 (Cost: {cost1:.2f})")
with res2:
    if cost2 < cost1:
        st.success(f"🏆 WINNER: Node 2 (Cost: {cost2:.2f})")
    else:
        st.error(f"❌ LOSER: Node 2 (Cost: {cost2:.2f})")

st.markdown("<br>", unsafe_allow_html=True)

# --- SECTION 4: Interactive Plots ---
plot_col1, plot_col2 = st.columns(2)

with plot_col1:
    # Plot 1: Fixed Bar Chart using Plotly
    df_bar = pd.DataFrame({
        "Node": ["Node 1 (High CPU)", "Node 2 (High Latency)"],
        "Total Penalty Cost": [cost1, cost2],
        "Color": ["Winner" if cost1 <= cost2 else "Loser", 
                  "Winner" if cost2 < cost1 else "Loser"]
    })
    
    fig_bar = px.bar(
        df_bar, x="Node", y="Total Penalty Cost", 
        color="Color", color_discrete_map={"Winner": "#00cc66", "Loser": "#ff4b4b"},
        title="Current Penalty Comparison",
        text_auto='.2f'
    )
    fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Penalty Cost")
    st.plotly_chart(fig_bar, use_container_width=True)

with plot_col2:
    # Plot 2: Sensitivity Line Graph
    # Sweeping Beta from 1 to 25 to see how the decision changes
    beta_range = list(range(1, 26))
    cost1_trend = [(cpu1 * alpha) + (lat1 * b) for b in beta_range]
    cost2_trend = [(cpu2 * alpha) + (lat2 * b) for b in beta_range]
    
    df_line = pd.DataFrame({
        "Beta (Latency Weight)": beta_range,
        "Node 1 Cost": cost1_trend,
        "Node 2 Cost": cost2_trend
    })
    
    fig_line = px.line(
        df_line, x="Beta (Latency Weight)", y=["Node 1 Cost", "Node 2 Cost"],
        title="Sensitivity Analysis (Cost vs Latency Weight)",
        labels={"value": "Total Penalty Cost", "variable": "Legend"}
    )
    # Add a visual marker for our current Beta selection
    fig_line.add_vline(x=beta, line_width=2, line_dash="dash", line_color="white", annotation_text="Current Beta")
    st.plotly_chart(fig_line, use_container_width=True)