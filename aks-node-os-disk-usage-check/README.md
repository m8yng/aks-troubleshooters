# AKS Node OS Disk Usage Check

Diagnose OS disk usage on an AKS node by breaking down disk consumption per pod across writable layers, emptyDir volumes, container logs, and container images.

## Run

The script must be executed directly on the node. Use `kubectl debug` to open a privileged shell on the target node, then run:

```bash
curl -O https://raw.githubusercontent.com/m8yng/aks-troubleshooters/refs/heads/main/aks-node-os-disk-usage-check/aks-node-os-disk-usage-check.py
python3 aks-node-os-disk-usage-check.py
```

To show more than the default top 30 pods:

```bash
python3 aks-node-os-disk-usage-check.py 50
```

## Output

### `=== container ===`

Lists pods ranked by estimated total disk usage:

| Column | Description |
|--------|-------------|
| `Total` | Sum of Writable + emptyDir + Logs + ImgShare |
| `Writable` | Overlay upperdir (container writable layer) |
| `emptyDir` | `kubernetes.io~empty-dir` volumes under `/var/lib/kubelet/pods` |
| `Logs` | Container logs under `/var/log/pods` |
| `ImgRaw` | Full size of all images used by the pod |
| `ImgShare` | Image size divided by the number of pods sharing each image |

### `=== containerd ===`

Reports total disk usage for containerd directories:

- **containerd** – `/var/lib/containerd`
- **snapshots** – overlayfs snapshot layers
- **content** – content-addressable image blobs
- **Top snapshots** – the 20 largest individual snapshot `fs` directories

### `=== node disk ===`

Output of `df -h /` for overall root filesystem usage.

## Requirements

- Python 3
- `crictl` available on the node
- Must run as root (or with sufficient privileges to read `/proc/self/mountinfo`, `/var/lib/kubelet`, `/var/lib/containerd`, and `/var/log`)
