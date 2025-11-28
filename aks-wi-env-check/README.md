## Workload-Identity Environment Checking

### Image spec:

docker hub: m8yng/aks-wi-env-check (linux/arm64, linux/amd64)

SDK Language:
Go: azure-sdk-for-go/sdk/azidentity
Python: azure-identity

### Usage:

Step 0: Create service account with identity:
Replace workload-identity-identity to your target` identity
```shell
CLIENT_ID=$(az identity show --name workload-identity-identity --resource-group rg-delete1 --query "clientId" -o tsv)
kubectl create serviceaccount workload-identity-sa -n default
kubectl annotate serviceaccount workload-identity-sa -n default \
  azure.workload.identity/client-id="${CLIENT_ID}"
```

Step 1: Update `pod.yaml` (set `LANG_EXT` to `py` or `go` as needed).

Step 2: Deploy and watch for the logs:
```shell
kubectl apply -f ./pod.yaml
kubectl logs aks-wi-env-check-pod -f
```

Notes:
- Pod runs once and stays `Completed` so logs remain.
- RBAC tests (listing subscriptions/resource groups) log WARN on 401/403 instead of failing the pod; add Reader/Contributor if you need those checks to pass.

Step 3: Clean-up after checking
```shell
kubectl delete -f ./pod.yaml
```
