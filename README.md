# ComfyUI Intel Installer (Python GUI Fork)

This is a user-friendly, pure Python installer for setting up ComfyUI to run on Intel GPUs (Arc and Integrated) using IPEX. It provides a modern, graphical interface built with the **CustomTkinter** library.

This project is a complete Python rewrite that modernizes the C++/PowerShell installer originally created by **a-One-Fan**, offering a more robust and maintainable solution for end-users.

*(Recommendation: Replace the link above with an actual screenshot of the new UI)*

## Features

- **Modern GUI:** Clean, dark-themed interface that works on Windows, macOS, and Linux.
- **Pure Python:** No need for C++ compilers. Runs on any system with a recent Python version.
- **Automated Dependency Checks:** Verifies that Git and Conda are installed and available.
- **One-Click Installation:** Clones ComfyUI, creates a dedicated Conda environment, installs all necessary dependencies (Torch, IPEX), and applies required patches.
- **Curated Model Downloader:** A simple list of essential models and tools (Flux, SDXL, Brushnet) that can be downloaded with a click.
- **Robust Downloads:** Correctly handles downloads from both HuggingFace and **Google Drive**.
- **Easy to Maintain:** All URLs, package versions, and model lists are stored in `config.json`, allowing for easy updates without changing the code.

## Prerequisites

1.  **Python 3.10 or newer:** Make sure Python is installed and added to your system's PATH.
2.  **Git:** Required for cloning repositories. Download from [git-scm.com](https://git-scm.com/downloads).
3.  **Miniconda/Anaconda:** The installer automates environment creation using Conda. Download from [Miniconda](https://docs.anaconda.com/miniconda/index.html).
    - **Important:** Install Conda to a path that **does not contain spaces** (e.g., `C:\miniconda3` instead of `C:\Program Files\miniconda3`). This is a common point of failure for many Python tools.

## How to Run

1.  **Clone this repository:**
    First, get the files for this installer. You can do this by cloning the repository using Git:
    ```bash
    git clone https://github.com/aequanima/ComfyUI-Intel-Installer-Script-UI.git
    cd ComfyUI-Intel-Installer-Script-UI
    ```

2.  **Install Python dependencies:**
    This installer requires a few packages to function. You can install them with pip:
    ```bash
    # For the GUI, downloader, and Windows-specific features
    pip install customtkinter requests gdown pypiwin32
    ```
    *(Note: `pypiwin32` is only needed for Windows to create shortcuts.)*

3.  **Run the installer:**
    ```bash
    python installer_ui.py
    ```

## Usage

1.  **Install Tab:**
    - The application will automatically check for Git and Conda and show their status at the top.
    - If all checks pass, the "Install / Update ComfyUI" button will be enabled.
    - Click it to begin the installation. You can monitor the process in the "Log" tab.

2.  **Download Models Tab:**
    - After the main installation is complete, go to this tab.
    - Check the boxes next to the models you wish to download.
    - Click "Download Selected Models". If a model has a license, you will be prompted to agree to it.

3.  **Log Tab:**
    - This tab shows detailed output from all operations, which is useful for troubleshooting if something goes wrong.

## Acknowledgements

This project stands on the shoulders of others. Full credit for the original C++/PowerShell installer goes to **a-One-Fan**. This Python version was directly inspired by the fork and modifications maintained by **aequanima**. Thank you both for your contributions to the community.

- **Original Creator:** [**a-One-Fan/ComfyUI-Intel-Installer-Script**](https://github.com/a-One-Fan/ComfyUI-Intel-Installer-Script)
- **Inspiration for this Fork:** [**aequanima/ComfyUI-Intel-Installer-Script-UI**](https://github.com/aequanima/ComfyUI-Intel-Installer-Script-UI)
