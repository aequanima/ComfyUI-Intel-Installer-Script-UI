import customtkinter as ctk
from tkinter import messagebox
import queue
import os
from installer_logic import InstallerLogic

# --- CustomTkinter Settings ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ComfyUI Intel Installer")
        self.geometry("800x650")
        
        # This will now check for the icon without crashing if the folder is missing
        icon_path = "assets/icon.ico"
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"Could not load icon: {e}")
        else:
            print("Could not find icon.ico. To add one, create an 'assets' folder with the icon inside.")


        self.status_queue = queue.Queue()
        self.logic = InstallerLogic(status_queue=self.status_queue)
        self.model_data = self.logic.config.get('model_collections', [])
        self.model_checkboxes = {}

        self.create_widgets()
        self.check_dependencies()
        self.after(100, self.process_queue)

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Top frame for status
        top_frame = ctk.CTkFrame(self, corner_radius=0)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        self.gpu_label = ctk.CTkLabel(top_frame, text="GPU: Detecting...", font=("Segoe UI", 12, "bold"))
        self.gpu_label.pack(anchor="w", padx=10, pady=5)
        self.git_label = ctk.CTkLabel(top_frame, text="Git: Checking...")
        self.git_label.pack(anchor="w", padx=10)
        # --- THIS IS THE CORRECTED LINE ---
        self.conda_label = ctk.CTkLabel(top_frame, text="Conda: Checking...")
        self.conda_label.pack(anchor="w", padx=10, pady=(0, 5))

        # Main tab view
        self.tab_view = ctk.CTkTabview(self, anchor="w")
        self.tab_view.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.tab_view.add("Install")
        self.tab_view.add("Download Models")
        self.tab_view.add("Log")

        self.create_install_tab()
        self.create_download_tab()
        self.create_log_tab()
        
        # Bottom frame for progress
        progress_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        progress_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        progress_frame.grid_columnconfigure(1, weight=1)

        self.progress_label = ctk.CTkLabel(progress_frame, text="Ready")
        self.progress_label.grid(row=0, column=0, padx=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(progress_frame, orientation="horizontal")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=1, sticky="ew")
    
    def create_install_tab(self):
        install_tab = self.tab_view.tab("Install")
        install_tab.grid_columnconfigure(0, weight=1)

        self.install_nodes_var = ctk.BooleanVar(value=True)
        install_nodes_check = ctk.CTkCheckBox(install_tab, text="Install Recommended Custom Nodes (GGUF, SUPIR, etc.)", variable=self.install_nodes_var)
        install_nodes_check.pack(anchor="w", pady=15, padx=20)

        self.install_button = ctk.CTkButton(install_tab, text="Install / Update ComfyUI", command=self.run_installation, height=40, state="disabled")
        self.install_button.pack(pady=20, padx=20, fill="x")

    def create_download_tab(self):
        download_tab = self.tab_view.tab("Download Models")
        
        scrollable_frame = ctk.CTkScrollableFrame(download_tab, label_text="Available Models")
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        for i, collection in enumerate(self.model_data):
            checkbox = ctk.CTkCheckBox(scrollable_frame, text=collection['name'])
            checkbox.pack(anchor="w", padx=10, pady=5)
            self.model_checkboxes[i] = checkbox

        download_button = ctk.CTkButton(download_tab, text="Download Selected Models", command=self.run_download, height=40)
        download_button.pack(pady=10, padx=10, fill="x")

    def create_log_tab(self):
        log_tab = self.tab_view.tab("Log")
        self.log_text = ctk.CTkTextbox(log_tab, wrap=tk.WORD, state="disabled", corner_radius=0)
        self.log_text.pack(fill="both", expand=True)

    def update_log(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def check_dependencies(self):
        gpu_info = self.logic.get_gpu_info()
        self.gpu_label.configure(text=f"GPU: {gpu_info}")

        git_ok = self.logic.check_git()
        self.git_label.configure(text="Git: Found", text_color="lightgreen" if git_ok else "red")
        if not git_ok: self.git_label.configure(text="Git: Not Found!")
        
        conda_ok = self.logic.find_conda()
        self.conda_label.configure(text="Conda: Found", text_color="lightgreen" if conda_ok else "red")
        if not conda_ok: self.conda_label.configure(text="Conda: Not Found!")
        
        if git_ok and conda_ok:
            self.install_button.configure(state="normal")
        else:
            self.update_log("Please install missing dependencies and restart the installer.")

    def run_installation(self):
        self.install_button.configure(state="disabled")
        self.tab_view.set("Install")
        self.logic.start_install(self.install_nodes_var.get())

    def run_download(self):
        models_to_download = []
        selected_collections = []

        for i, checkbox in self.model_checkboxes.items():
            if checkbox.get() == 1:
                selected_collections.append(self.model_data[int(i)])

        if not selected_collections:
            messagebox.showwarning("No Selection", "Please select one or more models to download.")
            return

        for collection in selected_collections:
            if collection.get('license'):
                 agree = messagebox.askyesno(
                     "License Agreement",
                     f"Model: {collection['name']}\n\nPlease review and agree to the model license at:\n{collection['license']}\n\nDo you agree to the terms?"
                 )
                 if not agree:
                     self.update_log(f"Skipping {collection['name']} due to license disagreement.")
                     continue
            models_to_download.extend(collection['files'])

        if models_to_download:
            self.tab_view.set("Download Models")
            self.logic.start_download(models_to_download)

    def process_queue(self):
        try:
            while True:
                message = self.status_queue.get_nowait()
                if message["type"] == "log":
                    self.update_log(message["data"])
                    if "--- Installation Finished" in message["data"] or "--- All selected models downloaded" in message["data"]:
                        self.install_button.configure(state="normal")
                elif message["type"] == "progress":
                    self.progress_bar.set(message["value"] / 100)
                    self.progress_label.configure(text=message["text"])
                    if "Failed" in message["text"]:
                        self.install_button.configure(state="normal")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

if __name__ == "__main__":
    app = App()
    app.mainloop()
