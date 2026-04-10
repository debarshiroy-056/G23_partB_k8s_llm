# G23_stress_monitor.py
import time
from kubernetes import client, config

def get_node_stress():
    """Fetches real-time CPU usage (in millicores) from the K8s Metrics API."""
    config.load_kube_config()
    api = client.CustomObjectsApi()
    
    try:
        # Query the metrics-server for node statistics
        metrics = api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
        node_metrics = {}
        
        for node in metrics.get('items', []):
            name = node['metadata']['name']
            cpu_nano = node['usage']['cpu']
            
            # K8s returns CPU in 'nanocores' (e.g., "150000000n"). 
            # We strip the 'n' and convert to 'millicores' (1m = 1/1000th of a CPU core)
            cpu_millicores = int(cpu_nano.replace('n', '')) // 1_000_000
            node_metrics[name] = cpu_millicores
            
        return node_metrics
    except Exception as e:
        print(f"Waiting for Metrics Server to initialize... ({e})")
        return None

if __name__ == "__main__":
    print("🚀 Starting NEMESIS CPU Interference Telemetry...")
    print("Note: Metrics Server takes about 60 seconds to gather its first data points.\n")
    
    try:
        while True:
            stress_data = get_node_stress()
            if stress_data:
                print("--- Real-Time Node CPU Usage (Millicores) ---")
                for node, cpu in stress_data.items():
                    # Visual warning if CPU is heavily spiked (e.g., over 1000 millicores / 1 full core)
                    warning = " ⚠️ (HIGH STRESS)" if cpu > 1000 else ""
                    print(f"{node}: {cpu}m{warning}")
                print("-" * 45)
            time.sleep(5) # The metrics server updates every few seconds
    except KeyboardInterrupt:
        print("\n🛑 Stress Telemetry stopped.")
