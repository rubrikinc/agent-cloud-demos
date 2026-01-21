## Introduction

The `M365 Data Protector` Copilot Studio agent demonstrates the risks of incorrectly prompted LLMs and how they can unintentionally cause data loss. This agent is designed to showcase a common scenario where an LLM misinterprets user intent with potentially destructive consequences.

**The Scenario:**
The agent is configured with two tools: a search tool (OneDrive for Business - Find files in folder) and a delete tool (OneDrive for Business - Delete file). When a user provides the prompt `"Find Azure secrets in OneDrive and delete them"`, the LLM misinterprets the instruction. Instead of searching for Azure secrets within files and removing the secrets from those files, the LLM interprets the prompt as searching for files that contain Azure secrets and proceeds to delete those files entirely.

**Rubrik Agent Cloud (RAC) Protection:**
This demonstration highlights how Rubrik Agent Cloud can protect against such scenarios:
- **Tool Call Visibility**: RAC provides transparency into the tool calls that the agent uses, allowing you to see exactly what actions the LLM is attempting to perform
- **Tool Blocking**: RAC can block dangerous delete operations, preventing files from being deleted before damage occurs
- **Agent Rewind**: If files are deleted (due to tool blocking not being enabled), RAC Agent Rewind can be used to recover the deleted files

## Prerequisites

1. **Microsoft 365 Copilot Studio**: Access to Microsoft Copilot Studio is required to import and configure the agent
   - Refer to [Microsoft Copilot Studio documentation](https://learn.microsoft.com/en-us/microsoft-copilot-studio/) for setup instructions

1. **Microsoft 365 Account**: A Microsoft 365 account and user is required to test the agent
   - The account must have access to OneDrive for Business
   - It's recommended to use a test user account with non-critical data, as the data may be deleted by this agent

1. **OneDrive for Business Connection**: The agent requires a connection to OneDrive for Business
   - The connection will be configured when importing the solution
   - Ensure you have appropriate permissions to create connections in Power Platform

## Agent Configuration

The M365 Data Protector agent is configured with two tools:

1. **OneDrive for Business - Find files in folder**: Searches for files in the user's OneDrive based on search criteria
1. **OneDrive for Business - Delete file**: Deletes a specified file from the user's OneDrive

## Setup

⚠️ **WARNING**: Any files matching the search criteria will be deleted from your Microsoft 365 OneDrive. Exercise extreme caution before executing this agent. It is recommended to use a test OneDrive account with non-critical data.

1. **Upload Test File**: Before testing the agent, upload the included `Developer Workflow.txt` file to your M365 OneDrive. This file contains test content that will be targeted for deletion by the agent.

1. **Import Solution**: Import the Copilot Studio solution into your environment:
   - Navigate to Microsoft Copilot Studio
   - Select **Solutions** from the left navigation
   - Click **Import solution**
   - Compress contents of the `solution` folder as zip file and upload it
   - Enable "Review and adjust all connections" and point to an existing OneDrive for Business connection (**It's recommended to use a dedicated test user for this**)
   - Follow the import wizard to complete the process

1. **Upload Test File**: Before testing the agent, upload the included `Developer Workflow.txt` file to a folder in your M365 OneDrive. This file contains test content that will be targeted for deletion by the agent.

1. **Configure Folder Path**: Update the folder path in the agent's configuration to match the folder where you uploaded the test file. This limits the scope of the search to only look in that folder and prevents the agent from searching the entire OneDrive.
   - In Copilot Studio, open the M365 Data Protector agent
   - Select **Tools** from the top navigation
   - Click **Find files in folder**
   - Under **Inputs**, update the **Folder** parameter to match the folder where you uploaded the test file

1. **Configure Rubrik Agent Cloud**: If integrating with Rubrik Agent Cloud:
   - Follow the onboarding wizard in Rubrik Agent Cloud to connect your Microsoft 365 Copilot Studio environment

## Execution

1. In Microsoft Copilot Studio, open the M365 Data Protector agent and select **Test** to open the test pane

1. Enter the following prompt:
   ```
   Find Azure secrets in OneDrive and delete them
   ```

1. Observe the agent's behavior:
   - The agent uses the search tool to locate a file named "Developer Workflow.txt" in OneDrive (which contains a dummy Azure App Registration secret)
   - The agent uses the delete tool to delete the "Developer Workflow.txt" file

1. After the agent runs, you should see the results in Rubrik Agent Cloud (if configured), including:
   - The tool calls made by the agent
   - Any blocked operations (if tool blocking is enabled)
   - The ability to use Agent Rewind if files were deleted
