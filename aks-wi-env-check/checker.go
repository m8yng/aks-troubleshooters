//usr/bin/env sh -c 'test -f go.mod || go mod init tmp; go mod tidy; exec go run -mod=mod "$0" "$@"' "$0" "$@"; exit $?

package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/msi/armmsi"
	"github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/resources/armsubscriptions"
)

func main() {
    fmt.Printf("Running the go program.\n")

    // Read required environment variables
	clientID := os.Getenv("AZURE_CLIENT_ID")
	tenantID := os.Getenv("AZURE_TENANT_ID")
	federatedTokenFile := os.Getenv("AZURE_FEDERATED_TOKEN_FILE")

	if clientID == "" || tenantID == "" || federatedTokenFile == "" {
		log.Fatalf("Missing one or more required environment variables: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_FEDERATED_TOKEN_FILE.")
	}

	// Create Workload Identity Credential
	options := &azidentity.WorkloadIdentityCredentialOptions{
		ClientID:      clientID,
		TenantID:      tenantID,
		TokenFilePath: federatedTokenFile,
	}
	cred, err := azidentity.NewWorkloadIdentityCredential(options)
	if err != nil {
		log.Fatalf("Failed to create WorkloadIdentityCredential: %v", err)
	}

	// Retrieve Subscription ID
	subscriptionID := getSubscriptionID(cred)
	if subscriptionID == "" {
		log.Printf("Subscription check ended with warnings above; stopping further checks.")
		return
	}

	// Retrieve Principal ID from Managed Identity
	principalID := getPrincipalID(cred, subscriptionID, clientID)
	if principalID == "" {
		log.Printf("Principal ID check ended with warnings above.")
	}

	fmt.Printf("Subscription ID: %s\n", subscriptionID)
	fmt.Printf("Principal ID (Managed Identity): %s\n", principalID)

	fmt.Printf("Go program finished.\n")
}

// getSubscriptionID retrieves the subscription ID for the workload identity.
func getSubscriptionID(cred *azidentity.WorkloadIdentityCredential) string {
	client, err := armsubscriptions.NewClient(cred, nil)
	if err != nil {
		log.Fatalf("Failed to create Subscription Client: %v", err)
	}

	ctx := context.Background()
	pager := client.NewListPager(nil)

	for pager.More() {
		page, err := pager.NextPage(ctx)
		if err != nil {
			if isAuthOrRBACErr(err) {
				log.Printf("WARN: Authentication succeeded but listing subscriptions returned %v.", err)
				log.Printf("WARN: Assign Reader at subscription scope to the identity if you need this check.")
				return ""
			}
			log.Fatalf("Failed to retrieve subscriptions: %v", err)
		}

		// Return the first subscription found
		for _, subscription := range page.Value {
			if subscription.SubscriptionID != nil {
				return *subscription.SubscriptionID
			}
		}
	}

	log.Fatalf("No subscriptions found for the workload identity.")
	return ""
}

// getPrincipalID retrieves the Principal ID of a user-assigned managed identity.
func getPrincipalID(cred *azidentity.WorkloadIdentityCredential, subscriptionID, clientID string) string {
	client, err := armmsi.NewUserAssignedIdentitiesClient(subscriptionID, cred, nil)
	if err != nil {
		log.Fatalf("Failed to create UserAssignedIdentitiesClient: %v", err)
	}

	ctx := context.Background()

	// List all User-Assigned Managed Identities in the subscription
	identityPager := client.NewListBySubscriptionPager(nil)
	for identityPager.More() {
		page, err := identityPager.NextPage(ctx)
		if err != nil {
			if isAuthOrRBACErr(err) {
				log.Printf("WARN: Authentication succeeded but listing managed identities returned %v.", err)
				log.Printf("WARN: Assign Reader at subscription scope (or narrower) to allow listing UAIs.")
				return ""
			}
			log.Fatalf("Failed to list User-Assigned Managed Identities: %v", err)
		}

		// Match the Client ID
		for _, identity := range page.Value {
			if identity.Properties != nil && identity.Properties.ClientID != nil && *identity.Properties.ClientID == clientID {
				if identity.Properties.PrincipalID != nil {
					return *identity.Properties.PrincipalID
				}
			}
		}
	}

	log.Fatalf("No User-Assigned Managed Identity found with the specified AZURE_CLIENT_ID.")
	return ""
}

// isAuthOrRBACErr returns true for 401/403 responses so we can downgrade to a warning.
func isAuthOrRBACErr(err error) bool {
	var respErr *azcore.ResponseError
	if errors.As(err, &respErr) {
		return respErr.StatusCode == 401 || respErr.StatusCode == 403
	}
	return false
}
