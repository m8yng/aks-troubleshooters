use std::env;

use reqwest::{Client, StatusCode};
use serde::Deserialize;
use tokio;

use azure_core::credentials::TokenCredential;
use azure_identity::WorkloadIdentityCredential;

#[derive(Deserialize)]
struct Subscription {
    #[serde(rename = "subscriptionId")]
    subscription_id: String,
    #[serde(rename = "displayName")]
    display_name: Option<String>,
}

#[derive(Deserialize)]
struct SubscriptionsList {
    value: Vec<Subscription>,
}

#[derive(Deserialize)]
struct ResourceGroup {
    name: String,
    location: String,
}

#[derive(Deserialize)]
struct ResourceGroupsList {
    value: Vec<ResourceGroup>,
}

fn log_step(msg: &str) {
    println!("[INFO] {msg}");
}

fn warn(msg: &str) {
    println!("[WARN] {msg}");
}

fn error(msg: &str) {
    eprintln!("[ERROR] {msg}");
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    log_step("Starting rust script execution...");

    let azure_client_id = env::var("AZURE_CLIENT_ID").unwrap_or_default();
    let azure_tenant_id = env::var("AZURE_TENANT_ID").unwrap_or_default();
    let azure_authority_host = env::var("AZURE_AUTHORITY_HOST").unwrap_or_default();
    let azure_federated_token_file = env::var("AZURE_FEDERATED_TOKEN_FILE").unwrap_or_default();

    println!("AZURE_CLIENT_ID: {azure_client_id}");
    println!("AZURE_TENANT_ID: {azure_tenant_id}");
    println!("AZURE_AUTHORITY_HOST: {azure_authority_host}");
    println!("AZURE_FEDERATED_TOKEN_FILE: {azure_federated_token_file}");

    log_step("Environment variables retrieved successfully.");

    // Validate required WI env vars before attempting auth
    let mut missing = Vec::new();
    if azure_client_id.is_empty() {
        missing.push("AZURE_CLIENT_ID");
    }
    if azure_tenant_id.is_empty() {
        missing.push("AZURE_TENANT_ID");
    }
    if azure_federated_token_file.is_empty() {
        missing.push("AZURE_FEDERATED_TOKEN_FILE");
    }
    if !missing.is_empty() {
        error(&format!(
            "Missing required Workload Identity env vars: {}",
            missing.join(", ")
        ));
        println!("[ERROR] Verify azure.workload.identity/use label on the pod and client-id annotation on the service account.");
        return Ok(());
    }

    log_step("Initializing WorkloadIdentityCredential for authentication...");
    let scope = "https://management.azure.com/.default";
    log_step(&format!("Attempting to acquire token for scope: {scope}"));

    // Use defaults: AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_FEDERATED_TOKEN_FILE
    let credential = WorkloadIdentityCredential::new(None)?;

    let token = match credential.get_token(&[scope], None).await {
        Ok(t) => {
            println!("[INFO] Successfully authenticated! Token acquired.");
            t.token.secret().to_string()
        }
        Err(e) => {
            error(&format!("Failed to authenticate: {e}"));
            return Ok(());
        }
    };

    let http = Client::builder().build()?;

    // Subscription discovery
    let subscription_id = match get_subscription_id(&http, &token).await {
        Ok(Some(id)) => id,
        Ok(None) => {
            warn("Unable to retrieve a subscription ID (see warnings above). Exiting.");
            return Ok(());
        }
        Err(e) => {
            error(&format!("Failed to retrieve subscription ID: {e}"));
            return Ok(());
        }
    };

    // Resource group listing (permission check)
    if let Err(e) = list_resource_groups(&http, &token, &subscription_id).await {
        error(&format!("Failed to list resource groups: {e}"));
        return Ok(());
    }

    log_step("Rust script execution completed successfully (with warnings noted above if any).");
    Ok(())
}

async fn get_subscription_id(
    http: &Client,
    token: &str,
) -> Result<Option<String>, Box<dyn std::error::Error>> {
    log_step("Retrieving subscription ID via REST...");
    let url = "https://management.azure.com/subscriptions?api-version=2020-01-01";
    let resp = http.get(url).bearer_auth(token).send().await?;
    let status = resp.status();
    if status == StatusCode::UNAUTHORIZED || status == StatusCode::FORBIDDEN {
        warn(&format!(
            "Permission check could not list subscriptions (status {status}). Authentication succeeded but identity likely missing Reader at tenant scope."
        ));
        return Ok(None);
    }
    if !status.is_success() {
        return Err(format!("Subscription list call failed with status {status}").into());
    }
    let body: SubscriptionsList = resp.json().await?;
    if let Some(sub) = body.value.first() {
        log_step(&format!(
            "Subscription retrieved: {} ({})",
            sub.display_name.as_deref().unwrap_or(""),
            sub.subscription_id
        ));
        Ok(Some(sub.subscription_id.clone()))
    } else {
        Err("No subscriptions returned for this identity".into())
    }
}

async fn list_resource_groups(
    http: &Client,
    token: &str,
    subscription_id: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    log_step("Listing resource groups using REST...");
    let url = format!(
        "https://management.azure.com/subscriptions/{}/resourcegroups?api-version=2021-04-01",
        subscription_id
    );
    let resp = http.get(&url).bearer_auth(token).send().await?;
    let status = resp.status();
    if status == StatusCode::UNAUTHORIZED || status == StatusCode::FORBIDDEN {
        warn(&format!(
            "Permission check could not list resource groups (status {status}). Authentication succeeded but the managed identity is likely missing Reader/Contributor on the subscription."
        ));
        return Ok(());
    }
    if !status.is_success() {
        return Err(format!("Resource group list call failed with status {status}").into());
    }
    let body: ResourceGroupsList = resp.json().await?;
    log_step("API Call: GET /subscriptions/{subscription_id}/resourcegroups (permission check)");
    println!(
        "[INFO] Permission check passed: found {} resource group(s):",
        body.value.len()
    );
    for rg in body.value {
        println!(" - Name: {}, Location: {}", rg.name, rg.location);
    }
    Ok(())
}
