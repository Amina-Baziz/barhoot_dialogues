# Project Setup Guide

This guide provides step-by-step instructions to set up the project, install the necessary tools, and configure authentication for Google Cloud services. This is designed to be followed easily.

## Prerequisites

Before starting, ensure you have the following installed:
- **Git**: [Download Git](https://git-scm.com/downloads)
- **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
- **pip** (Python package installer)

---

## Step 1: Clone the Repository

First, you need to download the code to your machine.

1.  Open your terminal (Command Prompt on Windows, Terminal on Mac/Linux).
2.  Navigate to the folder where you want to keep the project.
3.  Run the following command:

    ```bash
    git clone https://github.com/oussd/using_llms.git
    cd using_llms
    ```

---

## Step 2: Set Up Conda Environment

We use `conda` to manage dependencies.

1.  **Install Conda**:
    If you don't have it, download **Miniconda** (lightweight) or **Anaconda**:
    - [Download Miniconda](https://docs.conda.io/en/latest/miniconda.html)

2.  **Create the Environment**:
    Run this command in your terminal (from the project folder):
    ```bash
    conda env create -f environment.yml
    ```

3.  **Activate the Environment**:
    ```bash
    conda activate using_llms
    ```

   *You should see `(using_llms)` appear at the start of your command line.*

---

## Step 2.1: Required Permissions & Authentication

 The project uses two different methods for authentication depending on the model:

 1.  **`chat.py` (Gemini)**: Uses the **API Key** from your `.env` file.
 2.  **`chat_claude.py` (Claude)**: Uses your **Google Cloud Credentials** (via `gcloud`).

 Therefore, to run **Claude**, your Google account (or Service Account) **MUST** have the following role on the project:

 - **Vertex AI User** (`roles/aiplatform.user`)

 *If you only plan to use Gemini, the API Key is sufficient.*

---

## Step 3: Install Google Cloud CLI

You need the `gcloud` command-line tool to authenticate.

### Windows
1.  Download the **Google Cloud CLI Installer**: [Download Here](https://cloud.google.com/sdk/docs/install#windows)
2.  Run the installer and follow the prompts.
3.  Make sure to leave the boxes checked to start the shell after installation.

### Mac / Linux
Run the following commands in your terminal:

```bash
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
tar -xf google-cloud-cli-linux-x86_64.tar.gz
./google-cloud-sdk/install.sh
```

Restart your terminal after installation to ensure `gcloud` is in your path.

---

## Step 4: Authenticate & Connect to Project

This step involves logging in and connecting your local machine to your Google Cloud Project.

1.  **Initialize gcloud**:
    Run this command and follow the interactive prompts to log in with your Google account.
    ```bash
    gcloud init
    ```
    - Pick option [2] to Create a new configuration if asked.
    - Log in via the browser window that pops up.
    - Select the project: `prj-udst-prod-oussama-1` (or your specific project ID if different).

2.  **Set up Application Default Credentials (ADC)**:
    **IMPORTANT**: This is the "proper service account" step for local development. It allows the Python scripts to act on your behalf.
    
    ```bash
    gcloud auth application-default login
    ```
    - A browser window will open again.
    - Allow access.
    - You will see a message in the terminal saying `Credentials saved to file...`.

---

## Step 5: Configure API Keys

The application also requires a specific API key for Vertex AI / Gemini.

1.  **Create the .env file**:
    Copy the example file to a new file named `.env`.
    
    - **Mac/Linux**:
      ```bash
      cp .env.example .env
      ```
    - **Windows**:
      ```bash
      copy .env.example .env
      ```

2.  **Enter your API Key**:
    Open the `.env` file in a text editor (Notepad, Nano, VS Code, etc.).
    
    Change the line:
    ```text
    VERTEX_AI_KEY=your_api_key_here
    ```
    to:
    ```text
    VERTEX_AI_KEY=AIzaSy... (paste your actual key here)
    ```
    
    *Save the file.*

---

## Step 6: Run the Application

You are now ready to run the chat scripts.

**To run the standard chat:**
```bash
python chat.py
```

**To run the Claude chat:**
```bash
python chat_claude.py
```

---

## Troubleshooting

- **"gcloud command not found"**: Restart your terminal or reinstall the Google Cloud CLI.
- **"Module not found" error**: Ensure you activated your virtual environment (`source venv/bin/activate`) and ran `pip install -r requirements.txt`.
- **403 Permission Denied**: Ensure you ran `gcloud auth application-default login` and are logged into the account that has permissions for `prj-udst-prod-oussama-1`.
