# main.py
import os
import sys
import threading
import time
import logging
import psutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, List
from urllib.parse import urlparse

import httpx 

# Local imports
from __version__ import __version__, __author__, __copyright__
from utils.config import ConfigManager
from core.hardware import HardwareMonitor
from core.model_manager import OllamaManager
from gui.tray import TrayIcon
from gui.main_window import MainWindow # Use the new Main Window

def setup_logging():
    """Setup logging configuration for LMM."""
    log_dir = os.path.join(os.getenv('APPDATA'), 'LMM', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(
        log_dir, 
        f'lmm_{datetime.now().strftime("%Y%m%d")}.log'
    )
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    
    console_handler = logging.StreamHandler()
    
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    )
    console_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    logger = logging.getLogger('LMM')
    logger.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class LMMApp:
    """Main application class for Local Model Manager."""
    
    def __init__(self):
        self.logger = setup_logging()
        self.logger.info(f"Starting Local Model Manager v{__version__}")
        
        self.config = ConfigManager()
        self.settings = self.config.settings 
        self.polling_interval = self.config.get('polling_interval', 1)
        
        self.hardware_monitor = HardwareMonitor()
        self.ollama_manager = OllamaManager()
        
        self.http_client: Optional[httpx.Client] = None
        self._init_http_client()

        # Initialize the GUI (Main Window)
        # We pass 'self' so the GUI can access logic
        self.main_window = MainWindow(self)
        self.main_window.withdraw() # Start hidden

        self.tray_icon = TrayIcon(self) 
        
        self.overall_status = "Initializing..."
        self.current_ollama_model = "Waiting..."
        self.gpu_info = self.hardware_monitor.get_gpu_info()
        self.active_external_models = []

        self.should_run = True
        self.update_status_immediately = False 

    def _init_http_client(self):
        """Initialize HTTP client for Ollama API with current settings."""
        if self.http_client:
            self.http_client.close() 
        
        try:
            api_url = self.config.get('api_url')
            parsed_url = urlparse(api_url)
            
            self.logger.info(f"Initializing HTTP client with URL: {api_url}")
            
            client_config = {
                'verify': False,
                'follow_redirects': True,
                'timeout': 2 
            }

            if parsed_url.username and parsed_url.password:
                auth = (parsed_url.username, parsed_url.password)
                client_config['auth'] = auth
                self.logger.info("Using URL authentication")

            self.http_client = httpx.Client(**client_config)
            self.logger.info("HTTP client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing HTTP client: {str(e)}")
            self.http_client = None 

    def get_ollama_model_status(self) -> str:
        if not self.http_client:
            return "Ollama API Error"

        try:
            response = self.http_client.get(
                f'{self.config.get("api_url")}/api/ps'
            )
            
            if response.status_code == 200:
                data = response.json()
                running_models = data.get('models', [])
                
                if running_models:
                    model = running_models[0]
                    model_info = (
                        f"{model['name']} "
                        f"({model['details']['parameter_size']})"
                    )
                    return model_info
                else:
                    return "No Ollama Model Running"
            else:
                self.logger.warning(f"Ollama API returned status code: {response.status_code}")
                return "Ollama Not Running"
            
        except httpx.TimeoutException:
            self.logger.error("Ollama API request timed out.")
            return "Ollama Not Running"
            
        except httpx.ConnectError as e:
            self.logger.error(f"Connection error to Ollama API: {str(e)}")
            return "Ollama Not Running"
            
        except Exception as e:
            self.logger.error(f"Unexpected error in get_ollama_model_status: {str(e)}")
            return "Ollama API Error"

    def get_external_model_status(self) -> List[str]:
        running_external_models = []
        external_models_config = self.settings.get('external_models', [])
        
        try:
            running_process_names = {p.info['name'].lower() for p in psutil.process_iter(['name'])}
        except Exception:
            running_process_names = set()

        for ext_model in external_models_config:
            proc_name = ext_model.get('process', '').lower()
            model_name = ext_model.get('name', 'Unknown')
            
            if proc_name in running_process_names:
                running_external_models.append(model_name)
                
        return running_external_models

    def get_overall_status(self) -> str:
        ollama_status = self.get_ollama_model_status()
        self.current_ollama_model = ollama_status 

        external_status_list = self.get_external_model_status()
        self.active_external_models = external_status_list
        
        gpu_info = self.hardware_monitor.get_gpu_info()
        self.gpu_info = gpu_info
        
        gpu_status_str = ""
        if gpu_info["vram_used"] != "N/A":
            gpu_status_str = f"GPU: {gpu_info['vram_used']} / {gpu_info['vram_total']}"
            if gpu_info["gpu_utilization"] != "N/A":
                gpu_status_str += f" ({gpu_info['gpu_utilization']})"
        elif self.hardware_monitor.nvml_initialized:
             gpu_status_str = "GPU: No VRAM Info"
        else:
            gpu_status_str = "GPU: N/A"

        status_parts = []
        if external_status_list:
            status_parts.append(f"Ext: {', '.join(external_status_list)}")

        if "Ollama API Error" in ollama_status:
            status_parts.append("Ollama: Error")
        elif "Ollama Not Running" in ollama_status:
            status_parts.append("Ollama: Offline")
        elif "No Ollama Model Running" not in ollama_status:
            status_parts.append(f"Ollama: {ollama_status}")
        
        if not status_parts:
             main_status = "Idle"
        else:
             main_status = " | ".join(status_parts)

        return f"{main_status} ({gpu_status_str})"

    def run(self):
        """Starts the main application loop."""
        
        # Start tray in a thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

        # GUI Event Loop must run in the main thread for Tkinter
        # To keep the polling loop running, we need to use root.after() in the GUI
        # But LMMApp has logic that was in a while loop.
        # We will move the polling logic into a method called by the GUI's mainloop
        
        self.main_window.after(1000, self._poll_status)
        self.main_window.mainloop()
        
    def _poll_status(self):
        """Called periodically by Tkinter main loop to update status."""
        if not self.should_run:
            self.main_window.quit()
            return

        # This replaces the while loop in the previous run() implementation
        # It just triggers the tray update if needed. 
        # The TrayIcon class has its own update_status_loop running in a thread, 
        # which calls get_overall_status().
        # However, Tkinter is not thread-safe. If tray updates touch GUI, it will crash.
        # TrayIcon uses pystray, which has its own loop.
        
        # Since we moved to main_window.mainloop(), the tray thread is fine as long as it doesn't touch Tkinter widgets directly.
        # The main_window updates ITSELF using its own .after() loop.
        
        if self.update_status_immediately:
             # We can't force the tray thread easily, but we can set flags
             # or just wait for the next poll
             pass

        self.main_window.after(int(self.polling_interval * 1000), self._poll_status)

    def stop(self):
        """Stops the application and cleans up resources."""
        self.logger.info("Stopping Local Model Manager...")
        self.should_run = False
        if self.http_client:
            self.http_client.close()
            self.logger.info("HTTP client closed.")
        self.tray_icon.stop()
        self.hardware_monitor.__del__() 
        self.logger.info("Local Model Manager stopped.")
        
        # Stop GUI
        self.main_window.quit()
        sys.exit(0) 

    def show_main_window(self):
        """Opens the unified main window."""
        # Must be called from main thread logic
        self.main_window.show_window()
        self.main_window._update_dashboard() # Trigger immediate update

    def save_settings(self):
        """Wrapper for ConfigManager save_settings."""
        self.config.save_settings()

if __name__ == "__main__":
    app = LMMApp()
    app.run()