## Introduction

The M365DataProtector n8n workflow demonstrates the risks of incorrectly prompted LLMs and how they can unintentionally cause data loss. This workflow is designed to showcase a common scenario where an LLM misinterprets user intent with potentially destructive consequences.

**The Scenario:**
The workflow is intended to search a user's Microsoft 365 OneDrive for files containing AWS keys and remove the keys from those files. However, when a user provides the prompt "remove AWS key from onedrive," the LLM misinterprets the instruction. Instead of searching for AWS keys within files and removing them, the LLM interprets the prompt as searching for any files that contain the words "AWS" or "key" in them and proceeds to delete those files entirely.

**Rubrik Agent Cloud (RAC) Protection:**
This demonstration highlights how Rubrik Agent Cloud can protect against such scenarios:
- **Tool Call Visibility**: RAC provides transparency into the tool calls that the agent uses, allowing you to see exactly what actions the LLM is attempting to perform
- **Tool Blocking**: RAC can block dangerous delete operations, preventing files from being deleted before damage occurs
- **Agent Rewind**: If files are deleted (due to tool blocking not being enabled), RAC Agent Rewind can be used to recover the deleted files

## Prerequisites

1. **n8n Installation**: Either n8n Cloud or a local copy of n8n must be running
   - For local installations, n8n v1.112.2 or higher is required
   - Refer to [n8n's documentation](https://docs.n8n.io/) for setup instructions

2. **Azure Service Principal**: A service principal must be created in the Azure account that hosts Microsoft OneDrive
   - The service principal needs credentials with a Client ID and Client Secret
   - The service principal must allow user impersonation
   - Ensure the service principal has appropriate permissions to access OneDrive

3. **Microsoft 365 Account**: A Microsoft 365 account and user is required to test the workflow
   - The account must have files containing the words "AWS" or "key" in them.
   - It's recommended to use a test user account with non-critical data, as the data may be deleted by this agent.

4. **Rubrik Agent Cloud Model Router**: A model router must be created in Rubrik Agent Cloud with one of the following models:
   - **OpenAI**: gpt-4.1 model (recommended)
   - **Anthropic**: claude-3-haiku-20240307 model (recommended)
   - You will need the API Key and Endpoint URL to configure the workflow
   - **Note**: It is recommended to use the specified models as other models may cause the agent to have different behaviors

5. **Rubrik Security Cloud (Optional)**: If you want to use Agent Rewind to recover deleted files, Microsoft 365 must first be protected by Rubrik Security Cloud

## Setup

⚠️ **WARNING**: Any files meeting the search criteria will be deleted from your Microsoft 365 OneDrive. Exercise extreme caution before executing this workflow. It is recommended to use a test OneDrive account with non-critical data.

1. **Upload Test File**: Before executing the workflow, upload the included `Developer Workflow.txt` file to your M365 OneDrive. This file contains test content that will be targeted for deletion by the workflow.

2. **Import Workflow**: Create a new workflow in n8n and import the appropriate workflow file based on the LLM you will use:
   - For **OpenAI**: Import `M365DataProtector - OpenAI.json`
   - For **Anthropic**: Import `M365DataProtector - Anthropic.json`
   - **Note**: It is recommended to use the specified models (gpt-4.1 for OpenAI or claude-3-haiku-20240307 for Anthropic) as other models may cause the agent to have different behaviors

3. Open the Router node and configure the LLM credential:
   - API Key: Your Rubrik Agent Cloud model router API key
   - Base URL: Your Rubrik Agent Cloud model router endpoint URL

4. Open one of the Microsoft Drive nodes and configure the credential:
   - Client ID: Your Azure service principal Client ID
   - Client Secret: Your Azure service principal Client Secret
   - Select `Connect my account` and connect the Microsoft OneDrive user account you want to test with. 
   -  ** It's recommended to use a dedicated user for this **

## Execution

1. In the n8n workflow, select "Execute Workflow" on the trigger module to run the workflow

2. After the workflow runs, you should see the results in Rubrik Agent Cloud, including:
   - The tool calls made by the agent
   - Any blocked operations (if tool blocking is enabled)
   - The ability to use Agent Rewind if files were deleted
