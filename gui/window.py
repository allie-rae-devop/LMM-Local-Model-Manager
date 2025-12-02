# gui/window.py
import os
import sys
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
import winreg
from urllib.parse import urlparse
import httpx # Will need this for the settings window API connection
import json # Will need this for loading/saving settings

# Assuming __version__, __author__, __copyright__ will be available globally or passed
# from __version__ import __version__, __author__, __copyright__

# Placeholder for now, will be properly integrated with LMM's logging
import logging
logger = logging.getLogger('LMM')

from core.model_manager import OllamaManager # Import OllamaManager

class SettingsWindow:
    """Settings window for LMM configuration."""

    def __init__(self, app_instance):
        """
        Initialize the settings window.

        Args:
            app_instance: Reference to the main LMM instance (main.py)
        """
        self.app_instance = app_instance
        self.window = tk.Tk()
        self.window.title("LMM - Settings") # Changed title
        self.window.geometry("400x460")
        self.window.resizable(False, False)
        
        # Set Windows theme
        self.style = ttk.Style()
        self.style.theme_use('vista')
        
        self._create_widgets()
        self._center_window()
        
        # Make window modal
        self.window.transient()
        self.window.grab_set()
        self.window.focus_set()
        
        # Handle window closing via X button
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        
        self.window.mainloop()
    
    def _create_widgets(self):
        """Create and arrange all window widgets."""
        # Title
        title_label = ttk.Label(
            self.window, 
            text="Local Model Manager", # Changed title
            font=('Segoe UI', 14, 'bold')
        )
        title_label.pack(pady=10)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(
            self.window, 
            text="General Settings", # Changed label
            padding=10
        )
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        # Startup setting
        self.startup_var = tk.BooleanVar(
            value=self.app_instance.settings.get('startup', False)
        )
        startup_check = ttk.Checkbutton(
            settings_frame,
            text="Run at Windows startup",
            variable=self.startup_var,
            command=self.toggle_startup
        )
        startup_check.pack(anchor="w", pady=5)
        
        # API Settings frame
        api_frame = ttk.LabelFrame(
            self.window, 
            text="Ollama API Connection", # Changed label
            padding=10
        )
        api_frame.pack(fill="x", padx=10, pady=5)
        
        # API URL setting
        url_frame = ttk.Frame(api_frame)
        url_frame.pack(fill="x", pady=2)
        
        ttk.Label(
            url_frame, 
            text="Ollama URL:"
        ).pack(side="left")
        
        self.api_url_var = tk.StringVar(
            value=self.app_instance.settings.get(
                'api_url', 
                f'http://localhost:11434' # Hardcoded for now, will use app_instance.DEFAULT_API_HOST etc. later
            )
        )
        url_entry = ttk.Entry(
            url_frame,
            textvariable=self.api_url_var,
            width=30
        )
        url_entry.pack(side="right")
        
        # Save API settings button
        save_api_btn = ttk.Button(
            api_frame,
            text="Save API Settings",
            command=self.save_api_settings
        )
        save_api_btn.pack(pady=5)

        # External Models Frame
        ext_models_frame = ttk.LabelFrame(
            self.window,
            text="External Models (Process Watcher)",
            padding=10
        )
        ext_models_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Listbox for external models
        self.ext_models_listbox = tk.Listbox(ext_models_frame, height=4, selectmode=tk.SINGLE)
        self.ext_models_listbox.pack(side="top", fill="both", expand=True, pady=5)
        
        # Load existing models
        self._load_ext_models()

        # Add/Remove inputs
        input_frame = ttk.Frame(ext_models_frame)
        input_frame.pack(fill="x", pady=5)

        ttk.Label(input_frame, text="Name:").pack(side="left")
        self.ext_name_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.ext_name_var, width=10).pack(side="left", padx=2)

        ttk.Label(input_frame, text="Process:").pack(side="left")
        self.ext_proc_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.ext_proc_var, width=10).pack(side="left", padx=2)

        ttk.Button(input_frame, text="Add", command=self._add_ext_model).pack(side="left", padx=5)
        ttk.Button(input_frame, text="Remove", command=self._remove_ext_model).pack(side="left")
        
        # About frame
        about_frame = ttk.LabelFrame(
            self.window, 
            text="About", 
            padding=10
        )
        about_frame.pack(fill="x", padx=10, pady=5)
        
        # Version info
        version_label = ttk.Label(
            about_frame, 
            text=f"Version: 0.1.0" # Placeholder for __version__
        )
        version_label.pack(anchor="w")
        
        # Description
        desc_label = ttk.Label(
            about_frame,
            text="Local Model Manager (LMM) helps you monitor and manage\nlocal AI models and resources.", # Changed description
            justify="left"
        )
        desc_label.pack(anchor="w", pady=5)
        
        # GitHub link
        github_link = ttk.Label(
            about_frame,
            text="GitHub Repository (Original Source)", # Changed text
            cursor="hand2",
            foreground="blue"
        )
        github_link.pack(anchor="w")
        github_link.bind(
            "<Button-1>", 
            lambda e: webbrowser.open(
                "https://github.com/ysfemreAlbyrk/ollama-monitor"
            )
        )
        
        # Close button
        close_btn = ttk.Button(
            self.window, 
            text="Close", 
            command=self.window.destroy
        )
        close_btn.pack(side="bottom", pady=10)
    
    def _center_window(self):
        """Center the window on the screen."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def toggle_startup(self):
        """Toggle Windows startup setting."""
        startup = self.startup_var.get()
        self.app_instance.settings['startup'] = startup
        self.app_instance.save_settings()
        
        key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, 
                key_path, 
                0, 
                winreg.KEY_ALL_ACCESS
            )
            
            if startup:
                # Use sys.executable for a more reliable path to the bundled .exe
                executable_path = sys.executable if hasattr(sys, 'frozen') else os.path.abspath(sys.argv[0])
                winreg.SetValueEx(
                    key, 
                    "LMM", # Changed name
                    0, 
                    winreg.REG_SZ, 
                    executable_path
                )
            else:
                try:
                    winreg.DeleteValue(key, "LMM") # Changed name
                except WindowsError:
                    pass
            
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to save startup setting: {str(e)}")
    
    def save_api_settings(self):
        """Save API settings and reinitialize client."""
        try:
            api_url = self.api_url_var.get().strip()
            
            # Basic URL validation
            parsed = urlparse(api_url)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValueError("Invalid URL format")
            
            # Save new settings
            self.app_instance.settings['api_url'] = api_url
            self.app_instance.save_settings()
            
            # Reinitialize client
            # if hasattr(self.app_instance, 'client'): # This will be handled in main.py
            #     self.app_instance.client.close()
            # self.app_instance._init_http_client() # This will be handled in main.py
            
            self.window.destroy()
            logger.info("API settings saved and connection updated!")
            # self.app_instance.icon.notify("API settings saved and connection updated!") # This will be handled by tray.py
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Invalid API URL: {str(e)}"
            )

    def _load_ext_models(self):
        """Load external models into listbox."""
        self.ext_models_listbox.delete(0, tk.END)
        models = self.app_instance.settings.get('external_models', [])
        for model in models:
            self.ext_models_listbox.insert(tk.END, f"{model['name']} ({model['process']})")

    def _add_ext_model(self):
        """Add a new external model."""
        name = self.ext_name_var.get().strip()
        process = self.ext_proc_var.get().strip()
        
        if not name or not process:
            messagebox.showwarning("Input Error", "Name and Process are required.")
            return
            
        if not process.endswith('.exe'):
             process += '.exe'

        new_model = {"name": name, "process": process, "type": "local_gpu"} # Default to GPU for now
        
        current_models = self.app_instance.settings.get('external_models', [])
        current_models.append(new_model)
        
        self.app_instance.settings['external_models'] = current_models
        self.app_instance.save_settings()
        
        self._load_ext_models()
        self.ext_name_var.set("")
        self.ext_proc_var.set("")

    def _remove_ext_model(self):
        """Remove selected external model."""
        selection = self.ext_models_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        current_models = self.app_instance.settings.get('external_models', [])
        
        if 0 <= index < len(current_models):
            del current_models[index]
            self.app_instance.settings['external_models'] = current_models
            self.app_instance.save_settings()
            self._load_ext_models()

# CustomMenuItem is also moved here as it's a GUI component
import pystray # Needed for CustomMenuItem

class CustomMenuItem(pystray.MenuItem):
    """Custom menu item with better visibility for disabled items."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def render(self, window, offset=(0, 0)):
        if not self.visible:
            return []
            
        # Use white color (or any other color) for disabled items
        text_color = 'white' if not self.enabled else 'black'
        
        return [(
            offset[0], offset[1],
            self.text,
            {
                'text': text_color,
                'background': None,
            }
        )]


class ModelManagerWindow:
    """
    Tkinter window for managing Ollama models (list, pull, delete).
    """
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.ollama_manager = OllamaManager()
        self.window = tk.Tk()
        self.window.title("LMM - Model Manager")
        self.window.geometry("600x500")
        self.window.resizable(False, False)

        self.style = ttk.Style()
        self.style.theme_use('vista')

        self._create_widgets()
        self._center_window()
        self._load_models()

        self.window.transient()
        self.window.grab_set()
        self.window.focus_set()
        
        # Handle window closing via X button
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        
        self.window.mainloop()

    def _create_widgets(self):
        title_label = ttk.Label(
            self.window,
            text="Ollama Model Manager",
            font=('Segoe UI', 14, 'bold')
        )
        title_label.pack(pady=10)

        # Model List Frame
        model_list_frame = ttk.LabelFrame(self.window, text="Installed Models", padding=10)
        model_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.model_listbox = tk.Listbox(model_list_frame, selectmode=tk.SINGLE)
        self.model_listbox.pack(side="left", fill="both", expand=True)
        self.model_listbox.bind("<<ListboxSelect>>", self._on_model_select)

        scrollbar = ttk.Scrollbar(model_list_frame, orient="vertical", command=self.model_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.model_listbox.config(yscrollcommand=scrollbar.set)

        # Action Buttons Frame
        action_buttons_frame = ttk.Frame(self.window, padding=10)
        action_buttons_frame.pack(fill="x", padx=10, pady=5)

        self.refresh_button = ttk.Button(
            action_buttons_frame,
            text="Refresh List",
            command=self._load_models
        )
        self.refresh_button.pack(side="left", padx=5)

        self.delete_button = ttk.Button(
            action_buttons_frame,
            text="Delete Selected Model",
            command=self._delete_selected_model,
            state=tk.DISABLED
        )
        self.delete_button.pack(side="left", padx=5)

        # Pull Model Frame
        pull_model_frame = ttk.LabelFrame(self.window, text="Pull/Install Model", padding=10)
        pull_model_frame.pack(fill="x", padx=10, pady=5)

        pull_input_frame = ttk.Frame(pull_model_frame)
        pull_input_frame.pack(fill="x")

        ttk.Label(pull_input_frame, text="Model Tag:").pack(side="left")
        self.model_tag_var = tk.StringVar()
        self.model_tag_entry = ttk.Entry(pull_input_frame, textvariable=self.model_tag_var, width=40)
        self.model_tag_entry.pack(side="left", fill="x", expand=True, padx=5)

        pull_button = ttk.Button(
            pull_input_frame,
            text="Pull Model",
            command=self._pull_model
        )
        pull_button.pack(side="right")

        # Close button
        close_btn = ttk.Button(
            self.window,
            text="Close",
            command=self.window.destroy
        )
        close_btn.pack(side="bottom", pady=10)

    def _center_window(self):
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def _on_model_select(self, event):
        selected_indices = self.model_listbox.curselection()
        if selected_indices:
            self.delete_button.config(state=tk.NORMAL)
        else:
            self.delete_button.config(state=tk.DISABLED)

    def _load_models(self):
        self.model_listbox.delete(0, tk.END)
        models = self.ollama_manager.list_models()
        if models:
            for model in models:
                self.model_listbox.insert(tk.END, f"{model['name']} ({model['size']})")
        else:
            self.model_listbox.insert(tk.END, "No Ollama models found or Ollama is not running.")
        self.delete_button.config(state=tk.DISABLED)

    def _pull_model(self):
        model_tag = self.model_tag_var.get().strip()
        if not model_tag:
            messagebox.showwarning("Input Error", "Please enter a model tag to pull.")
            return

        # Disable buttons during operation
        self.model_tag_entry.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)

        # Run pull operation in a separate thread to keep GUI responsive
        def pull_thread():
            logger.info(f"Initiating pull for model: {model_tag}")
            success = self.ollama_manager.pull_model(model_tag)
            self.window.after(0, lambda: self._pull_complete(success, model_tag)) # Update GUI on main thread

        threading.Thread(target=pull_thread, daemon=True).start()


    def _pull_complete(self, success: bool, model_tag: str):
        # Re-enable buttons
        self.model_tag_entry.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)
        
        if success:
            messagebox.showinfo("Pull Model", f"Model '{model_tag}' pull initiated successfully. Check Ollama logs for progress.")
            self._load_models() # Refresh list
        else:
            messagebox.showerror("Pull Model", f"Failed to pull model '{model_tag}'. See logs for details.")

    def _delete_selected_model(self):
        selected_indices = self.model_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a model to delete.")
            return

        selected_model_text = self.model_listbox.get(selected_indices[0])
        # Extract model name from "name (size)" format
        model_name = selected_model_text.split(' ')[0]

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{model_name}'?"):
            return

        # Disable buttons during operation
        self.model_tag_entry.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)

        # Run delete operation in a separate thread
        def delete_thread():
            logger.info(f"Initiating delete for model: {model_name}")
            success = self.ollama_manager.delete_model(model_name)
            self.window.after(0, lambda: self._delete_complete(success, model_name)) # Update GUI on main thread

        threading.Thread(target=delete_thread, daemon=True).start()

    def _delete_complete(self, success: bool, model_name: str):
        # Re-enable buttons
        self.model_tag_entry.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)

        if success:
            messagebox.showinfo("Delete Model", f"Model '{model_name}' deleted successfully.")
            self._load_models() # Refresh list
        else:
            messagebox.showerror("Delete Model", f"Failed to delete model '{model_name}'. See logs for details.")