# G23_custom_scheduler.py
import time
import subprocess
from kubernetes import client, config, watch

# --- MODULE A: Network Telemetry ---
def ping_node(ip_address):
    try:
        output = subprocess.check_output(
            ["ping", "-c", "1", ip_address], stderr=subprocess.STDOUT, universal_newlines=True
        )
        for line in output.split('\n'):
            if "time=" in line:
                return float(line.split("time=")[1].split(" ")[0])
        return float('inf')
    except:
        return float('inf')

def get_network_latency(v1):
    nodes = v1.list_node().items
    latency_dict = {}
    for node in nodes:
        name = node.metadata.name
        for address in node.status.addresses:
            if address.type == "InternalIP":
                latency_dict[name] = ping_node(address.address)
    return latency_dict

# --- MODULE B: Stress Telemetry ---
def get_cpu_stress(cust_api):
    try:
        metrics = cust_api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
        stress_dict = {}
        for node in metrics.get('items', []):
            name = node['metadata']['name']
            cpu_nano = node['usage']['cpu']
            stress_dict[name] = int(cpu_nano.replace('n', '')) // 1_000_000
        return stress_dict
    except:
        return {}

# --- MODULE C: The Brain (NEMESIS) ---
def calculate_best_node(v1, cust_api):
    print("\n🔍 Evaluating Nodes...")
    network_data = get_network_latency(v1)
    stress_data = get_cpu_stress(cust_api)
    
    best_node = None
    lowest_cost = float('inf')
    
    # We only want to schedule on worker nodes, not the control-plane
    workers = [n for n in network_data.keys() if "worker" in n]
    
    for node in workers:
        lat = network_data.get(node, 1000)
        cpu = stress_data.get(node, 1000)
        
        # The Cost Function: (CPU * 1 weight) + (Latency * 10 weight)
        # Latency is multiplied by 10 because a 100ms delay is catastrophic for PyTorch DDP
        cost = (cpu * 1) + (lat * 10)
        
        print(f"   -> {node} | CPU: {cpu}m | Latency: {lat}ms | Total Penalty Cost: {cost:.2f}")
        
        if cost < lowest_cost:
            lowest_cost = cost
            best_node = node
            
    print(f"🏆 Selected Target: {best_node} (Lowest Penalty)")
    return best_node

def schedule_pod(v1, pod_name, namespace, target_node):
    """Bypasses default scheduler and physically binds the pod to the target node."""
    target = client.V1ObjectReference(kind="Node", api_version="v1", name=target_node)
    meta = client.V1ObjectMeta(name=pod_name)
    binding = client.V1Binding(target=target, metadata=meta)
    
    try:
        v1.create_namespaced_binding(namespace=namespace, body=binding, _preload_content=False)
        print(f"✅ Successfully bound pod '{pod_name}' to node '{target_node}'!")
    except Exception as e:
        print(f"❌ Failed to bind pod: {e}")

def run_nemesis():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    cust_api = client.CustomObjectsApi()
    w = watch.Watch()
    
    print("🧠 NEMESIS Multi-Objective Scheduler is running...")
    print("Listening for Pending pods tagged with 'schedulerName: nemesis'...\n")
    
    # Watch the cluster for new pods
    for event in w.stream(v1.list_pod_for_all_namespaces):
        pod = event['object']
        
        # Only intercept pods that are Pending AND ask specifically for our scheduler
        if pod.status.phase == "Pending" and pod.spec.scheduler_name == "nemesis":
            # Avoid scheduling the same pod multiple times
            if not pod.spec.node_name:
                print(f"🔔 Intercepted Pending Pod: {pod.metadata.name}")
                
                # 1. Evaluate the cluster
                target_node = calculate_best_node(v1, cust_api)
                
                # 2. Bind the pod
                if target_node:
                    schedule_pod(v1, pod.metadata.name, pod.metadata.namespace, target_node)

if __name__ == "__main__":
    run_nemesis()
