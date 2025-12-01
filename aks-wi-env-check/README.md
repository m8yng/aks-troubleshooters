## Workload Identity Env Checker

Multi-arch test image that verifies Azure Workload Identity using Go, Python, or Rust. Each binary lives at `/app/checker-go`, `/app/checker-py`, `/app/checker-rs`.

Image: [m8yng/aks-wi-env-check](https://hub.docker.com/r/m8yng/aks-wi-env-check) (linux/amd64, linux/arm64)  
SDKs: Go `azidentity`, Python `azure-identity`, Rust `azure_identity` + REST calls.

### Quick start
1) Create a WI-enabled service account and annotate with the managed identity client ID.
```
CLIENT_ID=$(az identity show --name workload-identity-identity --resource-group <rg> --query clientId -o tsv)
kubectl create serviceaccount workload-identity-sa -n default
kubectl annotate serviceaccount workload-identity-sa -n default azure.workload.identity/client-id="${CLIENT_ID}"
```
2) Set `LANG_EXT` in `pod.yaml` to `py` (default), `go`, or `rs`.  
3) Deploy and read logs:
```
kubectl apply -f pod.yaml
kubectl logs aks-wi-env-check-pod -f
```

Notes: pod runs once (RestartPolicy Never) so logs stay available. RBAC checks log WARN on 401/403 so users see missing permissions without failing the pod; add Reader/Contributor if you want those checks to pass.

Cleanup:
```
kubectl delete -f pod.yaml
```
