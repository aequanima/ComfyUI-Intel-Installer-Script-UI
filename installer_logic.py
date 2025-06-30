import os
import sys
import subprocess
import threading
import json
import re
from pathlib import Path

# --- Dependency Imports (requires 'pip install requests gdown') ---
import requests
import gdown

# --- Platform-specific Imports ---
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import win32com.client

class InstallerLogic:
    def __init__(self, config_path="config.json", status_queue=None):
        self.config = self.load_config(config_path)
        self.status_queue = status_queue
        self.base_dir = Path.cwd()
        self.install_dir = self.base_dir / self.config['base_folder_name']
        self.conda_path = None
        self.is_dgpu = False

    def log(self, message):
        if self.status_queue:
            self.status_queue.put({"type": "log", "data": message})

    def set_progress(self, value, text=""):
        if self.status_queue:
            self.status_queue.put({"type": "progress", "value": value, "text": text})

    def load_config(self, config_path):
        with open(config_path, 'r') as f:
            return json.load(f)

    def run_command(self, command, cwd=None, env=None):
        self.log(f"Running command: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        for line in iter(process.stdout.readline, ''):
            self.log(line.strip())
        process.wait()
        return process.returncode

    def check_git(self):
        try:
            result = subprocess.run(['git', '--version'], capture_output=True, text=True, check=True)
            self.log(f"Git found: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("Error: Git is not installed or not in the system's PATH.")
            return False

    def find_conda(self):
        # Simplified conda search logic
        if IS_WINDOWS:
            possible_paths = [
                Path(os.environ.get("USERPROFILE", "")) / "miniconda3",
                Path(os.environ.get("USERPROFILE", "")) / "anaconda3",
            ]
            for path in possible_paths:
                conda_exe = path / "Scripts" / "conda.exe"
                if conda_exe.exists():
                    self.conda_path = path
                    self.log(f"Found Conda at: {self.conda_path}")
                    return True
        # Add Linux/macOS paths if needed
        self.log("Error: Conda not found in standard locations.")
        return False

    def get_gpu_info(self):
        if IS_WINDOWS:
            try:
                wmi = win32com.client.GetObject("winmgmts:")
                controllers = wmi.InstancesOf("Win32_VideoController")
                for controller in controllers:
                    name = controller.Name.lower()
                    if "intel" in name:
                        self.log(f"Found Intel GPU: {controller.Name}")
                        if "arc" in name:
                            self.is_dgpu = True
                            return f"Intel Arc (dGPU) - {controller.Name}"
                        else:
                            self.is_dgpu = False
                            return f"Intel Integrated (iGPU) - {controller.Name}"
            except Exception as e:
                self.log(f"Could not get GPU info via WMI: {e}")
                return "Unknown GPU"
        else: # Basic Linux check
             # A more robust check would use 'lshw' or similar tools
            return "Linux GPU (assuming dGPU)"


    def clone_or_pull(self, repo_url, target_dir):
        repo_name = Path(repo_url).stem
        repo_path = Path(target_dir) / repo_name
        
        if repo_path.exists():
            self.log(f"Updating {repo_name}...")
            self.run_command(['git', 'pull'], cwd=repo_path)
        else:
            self.log(f"Cloning {repo_name}...")
            self.run_command(['git', 'clone', repo_url, str(repo_path)])

    def _install_thread(self, install_custom_nodes):
        try:
            self.log("--- Starting ComfyUI Installation ---")
            self.set_progress(5, "Creating directories...")
            self.install_dir.mkdir(exist_ok=True)
            comfy_dir = self.install_dir / "ComfyUI"

            self.set_progress(10, "Cloning ComfyUI repository...")
            self.clone_or_pull(self.config['comfyui_repo'], self.install_dir)

            self.set_progress(20, "Setting up IPEX hijack...")
            self.clone_or_pull(self.config['ipex_hijack_repo'], comfy_dir / "comfy")

            # Note: This file patching method is fragile. A better method would be to provide the file.
            model_management_path = comfy_dir / "comfy" / "model_management.py"
            if model_management_path.exists():
                self.log("Patching model_management.py for IPEX...")
                content = model_management_path.read_text()
                # Use a unique comment to prevent re-patching
                if "# IPEX_HIJACK_APPLIED" not in content:
                    content = content.replace(
                        "import comfy.ipex as ipex",
                        "import comfy.ipex as ipex # IPEX_HIJACK_APPLIED\n    from ipex_to_cuda import ipex_init\n    ipex_init()"
                    )
                    model_management_path.write_text(content)

            self.set_progress(30, "Creating Conda environment...")
            env_path = self.install_dir / self.config['env_name']
            self.run_command([str(self.conda_path / "Scripts" / "conda.exe"), 'create', '-p', str(env_path), 'python=3.10', '-y'])
            
            # Pip install commands need to be run in the activated environment
            pip_exe = str(env_path / "Scripts" / "python.exe")
            
            self.set_progress(40, "Installing ComfyUI requirements...")
            self.run_command([pip_exe, '-m', 'pip', 'install', '-r', str(comfy_dir / 'requirements.txt')])
            
            self.set_progress(50, "Installing IPEX and Torch...")
            if IS_WINDOWS:
                key = 'windows_dgpu' if self.is_dgpu else 'windows_igpu'
            else:
                key = 'linux'
            torch_packages = self.config['pip_packages'][key]
            self.run_command([pip_exe, '-m', 'pip', 'install'] + torch_packages)
            
            self.set_progress(60, "Installing common packages...")
            self.run_command([pip_exe, '-m', 'pip', 'install'] + self.config['pip_packages']['common'])

            if install_custom_nodes:
                custom_nodes_dir = comfy_dir / "custom_nodes"
                for i, node in enumerate(self.config['custom_nodes']):
                    progress = 70 + int(15 * (i / len(self.config['custom_nodes'])))
                    self.set_progress(progress, f"Installing custom node: {node['name']}")
                    self.clone_or_pull(node['url'], custom_nodes_dir)
            
            self.set_progress(90, "Creating launch script...")
            self.create_launch_script()
            self.set_progress(95, "Creating shortcut...")
            self.create_shortcut()

            self.set_progress(100, "Installation Complete!")
            self.log("--- Installation Finished Successfully ---")

        except Exception as e:
            self.log(f"An error occurred during installation: {e}")
            self.set_progress(0, "Installation Failed!")

    def start_install(self, install_custom_nodes=True):
        thread = threading.Thread(target=self._install_thread, args=(install_custom_nodes,))
        thread.daemon = True
        thread.start()
        
    def create_launch_script(self):
        if IS_WINDOWS:
            script_path = self.install_dir / "start_comfyui_intel.bat"
            env_path = self.install_dir / self.config['env_name']
            content = f"""
@echo off
echo Activating Conda environment...
call "{self.conda_path}\\Scripts\\activate.bat" "{env_path}"
echo Launching ComfyUI...
cd /D "%~dp0\\ComfyUI"
python main.py --lowvram
pause
"""
            script_path.write_text(content)
            self.log(f"Created launch script at {script_path}")

    def create_shortcut(self):
        if IS_WINDOWS:
            shortcut_path = self.base_dir / "ComfyUI Intel.lnk"
            target_path = self.install_dir / "start_comfyui_intel.bat"
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.TargetPath = str(target_path)
            shortcut.WorkingDirectory = str(self.install_dir)
            shortcut.IconLocation = f"{os.environ['SystemRoot']}\\System32\\shell32.dll, 14"
            shortcut.save()
            self.log(f"Created shortcut at {shortcut_path}")
    
    def _download_thread(self, models_to_download):
        try:
            total_models = len(models_to_download)
            for i, model in enumerate(models_to_download):
                progress = int(100 * (i / total_models))
                
                url = model['url']
                dest_folder = self.install_dir / "ComfyUI" / "models" / model['dest']
                dest_folder.mkdir(parents=True, exist_ok=True)
                
                filename = model.get('filename') or Path(url.split('?')[0]).name
                dest_path = dest_folder / filename

                self.set_progress(progress, f"Downloading {filename}...")
                self.log(f"Downloading {filename} to {dest_path}")
                
                if dest_path.exists():
                    self.log(f"{filename} already exists. Skipping.")
                    continue

                if "drive.google.com" in url:
                    gdown.download(url, str(dest_path), quiet=False)
                else:
                    with requests.get(url, stream=True) as r:
                        r.raise_for_status()
                        with open(dest_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
            
            self.set_progress(100, "Downloads Complete!")
            self.log("--- All selected models downloaded. ---")

        except Exception as e:
            self.log(f"An error occurred during download: {e}")
            self.set_progress(0, "Download Failed!")

    def start_download(self, models_to_download):
        if not (self.install_dir / "ComfyUI").exists():
            self.log("Error: ComfyUI is not installed. Please run the installer first.")
            return
            
        thread = threading.Thread(target=self._download_thread, args=(models_to_download,))
        thread.daemon = True
        thread.start()
