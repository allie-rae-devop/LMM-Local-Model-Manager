# gui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import logging
import psutil
import sv_ttk # Dark mode goodness
from core.model_manager import OllamaManager
from core.game_mode import activate_game_mode
from core.hardware import HardwareMonitor
from core.powershell import run_hidden_powershell_cmd # For stopping ollama

logger = logging.getLogger('LMM')

class MainWindow(tk.Tk):
    """
    Unified Main Window for LMM with Tabs.
    """
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.ollama_manager = OllamaManager()
        
        self.title("Local Model Manager")
        self.geometry("900x650")
        self.minsize(600, 450)
        
        # Apply Sun Valley Dark Theme
        sv_ttk.set_theme("dark")

        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        self._create_layout()
        self._center_window()
        
    def hide_window(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        
    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _create_layout(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dashboard, text="Dashboard")
        self._build_dashboard_tab(self.tab_dashboard)
        
        self.tab_models = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_models, text="Model Manager")
        self._build_model_manager_tab(self.tab_models)
        
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_settings, text="Settings")
        self._build_settings_tab(self.tab_settings)
        
        self.tab_profiles = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_profiles, text="Profiles")
        self._build_profiles_tab(self.tab_profiles)

    # --- Tab Builders ---

    def _build_dashboard_tab(self, parent):
        # Top: System Info
        info_frame = ttk.LabelFrame(parent, text="System Status", padding=10)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        # Grid layout for info
        self.lbl_gpu_name = ttk.Label(info_frame, text="GPU: Detect...", font=('Segoe UI', 11, 'bold'))
        self.lbl_gpu_name.grid(row=0, column=0, sticky='w', padx=5)
        
        # Load container
        load_frame = ttk.Frame(info_frame)
        load_frame.grid(row=1, column=0, sticky='w', padx=5)
        ttk.Label(load_frame, text="Load: ", font=('Segoe UI', 9, 'bold')).pack(side='left')
        self.lbl_vram_usage = ttk.Label(load_frame, text="VRAM: ...")
        self.lbl_vram_usage.pack(side='left')
        
        self.lbl_temp = ttk.Label(info_frame, text="Temp: ...")
        self.lbl_temp.grid(row=2, column=0, sticky='w', padx=5)

        # Middle: Active Processes Treeview
        proc_frame = ttk.LabelFrame(parent, text="Active AI Processes", padding=10)
        proc_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview
        columns = ('pid', 'name', 'vram', 'type')
        self.proc_tree = ttk.Treeview(proc_frame, columns=columns, show='headings')
        self.proc_tree.heading('pid', text='PID')
        self.proc_tree.heading('name', text='Process / Model Name')
        self.proc_tree.heading('vram', text='VRAM (MB)')
        self.proc_tree.heading('type', text='Type')
        
        self.proc_tree.column('pid', width=60)
        self.proc_tree.column('name', width=300)
        self.proc_tree.column('vram', width=100)
        self.proc_tree.column('type', width=100)
        
        self.proc_tree.pack(side='left', fill='both', expand=True)
        
        sb = ttk.Scrollbar(proc_frame, orient='vertical', command=self.proc_tree.yview)
        sb.pack(side='right', fill='y')
        self.proc_tree.config(yscrollcommand=sb.set)
        
        # Action Bar below Treeview
        action_frame = ttk.Frame(parent, padding=5)
        action_frame.pack(fill='x', padx=10)
        
        ttk.Button(action_frame, text="Refresh", command=self._update_dashboard).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Stop / Kill Selected", command=self._stop_selected_process).pack(side='left', padx=5)
        
        # Quick Load Section
        ql_frame = ttk.LabelFrame(action_frame, text="Quick Load", padding=2)
        ql_frame.pack(side='right', padx=5)

        # Models
        ttk.Label(ql_frame, text="Model:").pack(side='left', padx=2)
        self.combo_quick_load = ttk.Combobox(ql_frame, state='readonly', width=15)
        self.combo_quick_load.pack(side='left', padx=2)
        ttk.Button(ql_frame, text="Go", width=4, command=self._quick_load_model).pack(side='left', padx=2)

        # Profiles (Placeholder)
        ttk.Label(ql_frame, text="Profile:").pack(side='left', padx=2)
        self.combo_profile_load = ttk.Combobox(ql_frame, state='readonly', width=15, values=["Coding", "Chat", "Default"])
        self.combo_profile_load.pack(side='left', padx=2)
        ttk.Button(ql_frame, text="Go", width=4, command=self._quick_load_profile).pack(side='left', padx=2)


        # Bottom: Game Mode
        btn_gamemode = ttk.Button(parent, text="ACTIVATE GAME MODE (Kill All AI)", command=self._on_game_mode_click)
        btn_gamemode.pack(fill='x', padx=10, pady=10, ipady=5)
        
        self.after(2000, self._update_dashboard)

    def _build_model_manager_tab(self, parent):
        # Split: Left (List), Right (Details/Actions)
        paned = ttk.PanedWindow(parent, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left Frame
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Installed Models").pack(anchor='w', padx=5, pady=2)
        self.mm_listbox = tk.Listbox(left_frame)
        self.mm_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        self.mm_listbox.bind('<<ListboxSelect>>', self._on_model_select)
        
        ttk.Button(left_frame, text="Refresh List", command=self._refresh_models).pack(fill='x', padx=5, pady=2)
        
        # Right Frame
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=2)
        
        ttk.Label(right_frame, text="Model Details", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.lbl_model_details = ttk.Label(right_frame, text="Select a model...", wraplength=300)
        self.lbl_model_details.pack(anchor='w', pady=10, fill='x')
        
        self.btn_delete_model = ttk.Button(right_frame, text="Delete Model", state='disabled', command=self._delete_model)
        self.btn_delete_model.pack(fill='x', pady=5)
        
        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(right_frame, text="Pull New Model").pack(anchor='w')
        self.entry_pull_tag = ttk.Entry(right_frame)
        self.entry_pull_tag.pack(fill='x', pady=2)
        ttk.Button(right_frame, text="Pull / Install", command=self._pull_model).pack(fill='x', pady=2)

        self._refresh_models()

    def _build_settings_tab(self, parent):
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 1. External Models
        ext_frame = ttk.LabelFrame(scrollable_frame, text="External Models (Process Watcher)", padding=10)
        ext_frame.pack(fill='x', padx=10, pady=5)
        
        self.list_ext_models = tk.Listbox(ext_frame, height=6)
        self.list_ext_models.pack(fill='x', pady=5)
        
        f_inputs = ttk.Frame(ext_frame)
        f_inputs.pack(fill='x')
        ttk.Label(f_inputs, text="Name:").pack(side='left')
        self.entry_ext_name = ttk.Entry(f_inputs, width=15)
        self.entry_ext_name.pack(side='left', padx=5)
        ttk.Label(f_inputs, text="Process (.exe):").pack(side='left')
        self.entry_ext_proc = ttk.Entry(f_inputs, width=15)
        self.entry_ext_proc.pack(side='left', padx=5)
        
        ttk.Button(f_inputs, text="Add", command=self._add_ext_model).pack(side='left', padx=5)
        ttk.Button(ext_frame, text="Remove Selected", command=self._del_ext_model).pack(fill='x', pady=5)
        
        self._refresh_ext_models_list()

        # 2. Startup
        start_frame = ttk.LabelFrame(scrollable_frame, text="Startup", padding=10)
        start_frame.pack(fill='x', padx=10, pady=5)
        self.var_startup = tk.BooleanVar(value=self.app_instance.settings.get('startup', False))
        ttk.Checkbutton(start_frame, text="Run LMM at Windows Startup", variable=self.var_startup, command=self._toggle_startup).pack(anchor='w')

        # 3. API
        api_frame = ttk.LabelFrame(scrollable_frame, text="Ollama API", padding=10)
        api_frame.pack(fill='x', padx=10, pady=5)
        self.var_api_url = tk.StringVar(value=self.app_instance.settings.get('api_url', 'http://localhost:11434'))
        ttk.Entry(api_frame, textvariable=self.var_api_url).pack(fill='x', pady=5)
        ttk.Button(api_frame, text="Save API URL", command=self._save_api_url).pack(anchor='e')
        
        # 4. About
        abt_frame = ttk.LabelFrame(scrollable_frame, text="About", padding=10)
        abt_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(abt_frame, text="Local Model Manager v0.1.0").pack(anchor='w')
        lbl_link = ttk.Label(abt_frame, text="GitHub Repo", foreground="#5599ff", cursor="hand2")
        lbl_link.pack(anchor='w')
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/allie-rae-devop/LMN-Local-Model-Manager"))

    def _build_profiles_tab(self, parent):
        ttk.Label(parent, text="Profiles Feature - Coming Soon", font=('Segoe UI', 14)).pack(expand=True)

    # --- Logic ---

    def _update_dashboard(self):
        # GPU Info
        gpu_info = self.app_instance.hardware_monitor.get_gpu_info()
        if gpu_info:
            self.lbl_gpu_name.config(text=f"GPU: {gpu_info.get('name', 'Unknown')}")
            vram_txt = f"{gpu_info.get('vram_used', '?')} / {gpu_info.get('vram_total', '?')} ({gpu_info.get('gpu_utilization', '?')})"
            self.lbl_vram_usage.config(text=vram_txt)
            self.lbl_temp.config(text=f"Temp: {gpu_info.get('temperature', '?')}")
            
            # --- Update Active Processes Tree ---
            # Keep track of what we've seen to avoid dupes (PID based)
            seen_pids = set()
            
            # Clear current
            for item in self.proc_tree.get_children():
                self.proc_tree.delete(item)
                
            # 1. Add Ollama Active Model (from API)
            ollama_status = self.app_instance.get_ollama_model_status()
            if "Running" not in ollama_status and "Error" not in ollama_status and "Idle" not in ollama_status and "No" not in ollama_status:
                 self.proc_tree.insert('', 'end', values=('API', ollama_status, '-', 'Ollama API'))

            # 2. Add GPU Processes (from Hardware Monitor)
            for p in gpu_info.get('processes', []):
                self.proc_tree.insert('', 'end', values=(p['pid'], p['name'], p.get('vram_used_mb', '?'), p['type']))
                seen_pids.add(p['pid'])

            # 3. Add External Models (from Process Watcher)
            # This finds things NOT on GPU (or not seen by NVML)
            # We need the full process info, not just names, so we redo the psutil check here locally or get richer data from main
            # Let's do a local psutil check against settings
            ext_models = self.app_instance.settings.get('external_models', [])
            for em in ext_models:
                target_exe = em.get('process', '').lower()
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'].lower() == target_exe:
                            if proc.info['pid'] not in seen_pids:
                                self.proc_tree.insert('', 'end', values=(proc.info['pid'], em.get('name', proc.info['name']), '-', 'External (CPU/Other)'))
                                seen_pids.add(proc.info['pid'])
                    except: pass


        if self.state() == 'normal':
            self.after(2000, self._update_dashboard)

    def _stop_selected_process(self):
        sel = self.proc_tree.selection()
        if not sel: return
        
        item = self.proc_tree.item(sel[0])
        pid = item['values'][0]
        name = item['values'][1]
        
        if str(pid) == "API":
            # Stop Ollama Model
            model_name = name.split(' ')[0] # Naive parse
            if messagebox.askyesno("Unload Model", f"Unload model '{model_name}'?"):
                # Run ollama run model "" to unload? or stop? 'stop' is not always standard in CLI without custom API.
                # Best way to unload in Ollama is to load an empty model or stop the server, but 'ollama stop' works in newer versions
                cmd = f"ollama stop {model_name}"
                run_hidden_powershell_cmd(cmd)
                messagebox.showinfo("Sent", f"Sent stop command for {model_name}")
        else:
            # Real Process
            if messagebox.askyesno("Kill Process", f"Force kill process {name} (PID: {pid})?"):
                try:
                    p = psutil.Process(int(pid))
                    p.terminate()
                    messagebox.showinfo("Success", f"Terminated {name}")
                    self._update_dashboard()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to kill: {e}")

    def _quick_load_model(self):
        model = self.combo_quick_load.get()
        if model:
            run_hidden_powershell_cmd(f"ollama run {model}") # This might open a shell? 'run' is interactive.
            # We should probably use 'pull' or just hit the API to 'generate' empty to load it?
            # For now, just alerting user this is a stub or basic attempt
            messagebox.showinfo("Load", f"Requesting load for {model} (Feature pending implementation)")
            
    def _quick_load_profile(self):
        profile = self.combo_profile_load.get()
        messagebox.showinfo("Profile", f"Loading profile {profile} (Stub)")

    def _on_game_mode_click(self):
        res = activate_game_mode()
        msg = f"Game Mode Result:\nTerminated: {len(res['terminated'])}\nFailed: {len(res['failed'])}"
        messagebox.showinfo("Game Mode", msg)

    # Model Manager Logic
    def _refresh_models(self):
        self.mm_listbox.delete(0, tk.END)
        models = self.ollama_manager.list_models()
        model_names = [m['name'] for m in models]
        for name in model_names:
            self.mm_listbox.insert(tk.END, name)
        
        # Update quick load combo
        self.combo_quick_load['values'] = model_names

    def _on_model_select(self, event):
        sel = self.mm_listbox.curselection()
        if sel:
            self.btn_delete_model.config(state='normal')
            model_name = self.mm_listbox.get(sel[0])
            self.lbl_model_details.config(text=f"Selected: {model_name}")
        else:
            self.btn_delete_model.config(state='disabled')

    def _pull_model(self):
        tag = self.entry_pull_tag.get()
        if tag:
            self.ollama_manager.pull_model(tag) 
            messagebox.showinfo("Pull", f"Pulling {tag} in background...")

    def _delete_model(self):
        sel = self.mm_listbox.curselection()
        if sel:
            model = self.mm_listbox.get(sel[0])
            if messagebox.askyesno("Delete", f"Delete {model}?"):
                self.ollama_manager.delete_model(model)
                self._refresh_models()

    # Settings Logic
    def _refresh_ext_models_list(self):
        self.list_ext_models.delete(0, tk.END)
        for m in self.app_instance.settings.get('external_models', []):
            self.list_ext_models.insert(tk.END, f"{m['name']} ({m['process']})")

    def _add_ext_model(self):
        name = self.entry_ext_name.get()
        proc = self.entry_ext_proc.get()
        if name and proc:
            if not proc.endswith('.exe'): proc += '.exe'
            curr = self.app_instance.settings.get('external_models', [])
            curr.append({"name": name, "process": proc, "type": "local_gpu"})
            self.app_instance.settings['external_models'] = curr
            self.app_instance.save_settings()
            self._refresh_ext_models_list()
            self.entry_ext_name.delete(0, tk.END)
            self.entry_ext_proc.delete(0, tk.END)

    def _del_ext_model(self):
        sel = self.list_ext_models.curselection()
        if sel:
            idx = sel[0]
            curr = self.app_instance.settings.get('external_models', [])
            if idx < len(curr):
                curr.pop(idx)
                self.app_instance.settings['external_models'] = curr
                self.app_instance.save_settings()
                self._refresh_ext_models_list()

    def _toggle_startup(self):
        pass 

    def _save_api_url(self):
        url = self.var_api_url.get()
        self.app_instance.settings['api_url'] = url
        self.app_instance.save_settings()
        messagebox.showinfo("Settings", "API URL Saved")
