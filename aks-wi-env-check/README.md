### Usage:

Create service account with identity: Replace workload-identity1-identity to your target` identity
```yaml
CLIENT_ID=$(az identity show --name workload-identity1-identity --resource-group rg-delete1 --query "clientId" -o tsv)
kubectl create serviceaccount workload-identity-sa -n default
kubectl annotate serviceaccount workload-identity-sa -n default \
  azure.workload.identity/client-id="${CLIENT_ID}"
```

Deploy the testing pod for validation:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: aks-wi-env-check-pod
  namespace: default
  labels:
    azure.workload.identity/use: "true"
spec:
  containers:
  - name: aks-wi-env-check-container
    image: m8yng/aks-wi-env-check:latest
    imagePullPolicy: Always
  serviceAccountName: workload-identity-sa # Change this to the appropriate service account name
  restartPolicy: Always
```
