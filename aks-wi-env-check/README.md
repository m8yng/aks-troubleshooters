## Workload-Identity Environment Checking

m8yng/aks-wi-env-check (linux/arm64, linux/amd64)

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

Step 1: After update the `pod.yaml`,

Step 2: Deploy and watch for the logs:
```shell
kubectl apply -f ./pod.yaml
kubectl logs aks-wi-env-check-pod -f
```

Step 3: Clean-up after checking
```shell
kubectl delete -f ./pod.yaml
```
