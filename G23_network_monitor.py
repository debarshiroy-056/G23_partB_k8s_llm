# G23_network_monitor.py
import subprocess
import time
from kubernetes import client, config

def get_node_ips():
    """Fetches the internal IP addresses of all Kubernetes nodes."""
    config.load_kube_config()
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items
    
    node_ips = {}
    for node in nodes:
        node_name = node.metadata.name
        # Find the InternalIP address
        for address in node.status.addresses:
            if address.type == "InternalIP":
                node_ips[node_name] = address.address
    return node_ips

def ping_node(ip_address):
    """Pings an IP address once and returns the latency in milliseconds."""
    try:
        # Removed the strict Mac 1ms timeout so it can capture the 100ms delay
        output = subprocess.check_output(
            ["ping", "-c", "1", ip_address], 
            stderr=subprocess.STDOUT, 
            universal_newlines=True
        )
        # Parse the output to find the 'time=X.XXX ms' string
        for line in output.split('\n'):
            if "time=" in line:
                time_ms = line.split("time=")[1].split(" ")[0]
                return float(time_ms)
        
        return float('inf') # Safety fallback if parsing fails
        
    except subprocess.CalledProcessError:
        return float('inf') # Return infinity if the ping fails/drops
    except Exception as e:
        print(f"Error occurred while pinging {ip_address}: {e}")
        return float('inf')

def generate_network_matrix():
    """Builds and returns the latency dictionary for the scheduler."""
    node_ips = get_node_ips()
    network_matrix = {}
    
    for node_name, ip in node_ips.items():
        latency = ping_node(ip)
        network_matrix[node_name] = latency
        
    return network_matrix

if __name__ == "__main__":
    print("🚀 Starting NEMESIS Network Telemetry Module...")
    try:
        while True:
            matrix = generate_network_matrix()
            print("\n--- Real-Time Network Matrix ---")
            for node, latency in matrix.items():
                # If latency is infinity, it means the node is totally unreachable
                if latency == float('inf'):
                    print(f"{node}: Unreachable (Packet Loss)")
                else:
                    print(f"{node}: {latency:.2f} ms")
            time.sleep(2) # Update every 2 seconds
    except KeyboardInterrupt:
        print("\n🛑 Telemetry stopped.")