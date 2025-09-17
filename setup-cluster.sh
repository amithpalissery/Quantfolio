#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Kubernetes Cluster Setup ---
if ! kubectl get pods -n kube-system 2>/dev/null | grep -q 'kube-apiserver'; then
    echo "No Kubernetes control-plane found. Initializing new cluster..."
    
    sudo kubeadm init --cri-socket=unix:///var/run/crio/crio.sock
    
    echo "Configuring kubectl for ubuntu user..."
    sudo mkdir -p /home/ubuntu/.kube
    sudo cp /etc/kubernetes/admin.conf /home/ubuntu/.kube/config
    sudo chown ubuntu:ubuntu /home/ubuntu/.kube/config
    
    export KUBECONFIG=/home/ubuntu/.kube/config
    
    echo "Applying Weave Net CNI..."
    sudo -u ubuntu kubectl apply -f https://github.com/weaveworks/weave/releases/download/v2.8.1/weave-daemonset-k8s.yaml
    
    echo "Waiting for node to become Ready..."
    until sudo -u ubuntu kubectl get nodes | grep -q ' Ready '; do
        sleep 5
    done
    
    echo "Removing control-plane taint..."
    sudo -u ubuntu kubectl taint node $(hostname) node-role.kubernetes.io/control-plane:NoSchedule- || true
    
    echo "Waiting for kube-system pods to be Ready..."
    until sudo -u ubuntu kubectl get pods -n kube-system | grep -Ev 'STATUS|Running' | wc -l | grep -q '^0$'; do
        sleep 5
    done
    
    echo "Kubernetes control-plane setup complete."
else
    echo "[INFO] Kubernetes already initialized, skipping kubeadm init."
fi
