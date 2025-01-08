#!/usr/bin/env python3

import os
import subprocess
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient


def log_step(message):
    """Utility function to log steps."""
    print(f"[INFO] {message}")


def get_subscription_id(credential):
    """Retrieve the subscription ID using SubscriptionClient."""
    log_step("Retrieving subscription ID using SubscriptionClient...")
    try:
        client = SubscriptionClient(credential)
        subscription = next(client.subscriptions.list())  # Get the first subscription
        log_step(f"Subscription retrieved: {subscription.display_name} ({subscription.subscription_id})")
        return subscription.subscription_id
    except Exception as e:
        print(f"[ERROR] Failed to retrieve subscription ID: {e}")
        return None


def main():
    log_step("Starting python script execution...")

    # Display environment variables for debugging
    azure_client_id = os.getenv('AZURE_CLIENT_ID', '')
    azure_tenant_id = os.getenv('AZURE_TENANT_ID', '')
    azure_authority_host = os.getenv('AZURE_AUTHORITY_HOST', '')
    azure_federated_token_file = os.getenv('AZURE_FEDERATED_TOKEN_FILE', '')

    print(f"AZURE_CLIENT_ID: {azure_client_id}")
    print(f"AZURE_TENANT_ID: {azure_tenant_id}")
    print(f"AZURE_AUTHORITY_HOST: {azure_authority_host}")
    print(f"AZURE_FEDERATED_TOKEN_FILE: {azure_federated_token_file}")

    log_step("Environment variables retrieved successfully.")

    # Use DefaultAzureCredential for Managed Identity
    log_step("Initializing DefaultAzureCredential for authentication...")
    credential = DefaultAzureCredential()

    # Retrieve the subscription ID dynamically
    subscription_id = get_subscription_id(credential)
    if not subscription_id:
        print("[ERROR] Unable to retrieve a subscription ID. Exiting.")
        return

    # Define the scope for token acquisition
    scope = "https://management.azure.com/.default"
    log_step(f"Attempting to acquire token for scope: {scope}")
    try:
        token = credential.get_token(scope)
        print("[INFO] Successfully authenticated! Token acquired.")
    except Exception as e:
        print(f"[ERROR] Failed to authenticate: {e}")
        return

    log_step("Authentication successful. Proceeding to initialize ResourceManagementClient...")

    # Initialize ResourceManagementClient with the retrieved subscription ID
    try:
        log_step(f"Initializing ResourceManagementClient for subscription: {subscription_id}...")
        resource_client = ResourceManagementClient(credential, subscription_id)
        log_step("ResourceManagementClient initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize ResourceManagementClient: {e}")
        return

    # Example API call: List resource groups
    log_step("Listing resource groups using ResourceManagementClient...")
    try:
        resource_groups = list(resource_client.resource_groups.list())
        log_step(f"API Call: GET /subscriptions/{subscription_id}/resourceGroups")
        print(f"[INFO] Found {len(resource_groups)} resource group(s):")
        for rg in resource_groups:
            print(f" - Name: {rg.name}, Location: {rg.location}")
    except Exception as e:
        print(f"[ERROR] Failed to list resource groups: {e}")
        return

    log_step("Python script execution completed successfully.")


if __name__ == '__main__':
    main()
