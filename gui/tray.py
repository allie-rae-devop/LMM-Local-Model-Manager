# gui/tray.py
import os
import threading
import time
import pystray
from PIL import Image
from typing import Optional
import logging

from gui.window import CustomMenuItem 
from core.game_mode import activate_game_mode

logger = logging.getLogger('LMM')

class TrayIcon:
    """Manages the system tray icon and its interactions."""

    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.icon: Optional[pystray.Icon] = None
        self.should_run = True
        self.current_status_message = "Initializing..."
        self.last_status_message = None 

        # Icon paths
        self.icons_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 
            'assets'
        )
        self.icon_red = os.path.join(self.icons_dir, 'icon_red.png')
        self.icon_blue = os.path.join(self.icons_dir, 'icon_blue.png')
        self.icon_green = os.path.join(self.icons_dir, 'icon_green.png')
        
    def create_icon_image(self, status: str) -> Image.Image:
        if "Not Running" in status or "Error" in status:
            icon_path = self.icon_red
        elif "No Ollama Model" in status and "Ext:" not in status:
            icon_path = self.icon_blue
        elif "Idle" in status:
             icon_path = self.icon_blue
        else:
            icon_path = self.icon_green
            
        return Image.open(icon_path)

    def create_menu(self) -> pystray.Menu:
        # Title Item (Disabled to look like header)
        title_item = pystray.MenuItem(
            f"STATUS: {self.current_status_message}",
            lambda _: None,
            enabled=False
        )

        return pystray.Menu(
            title_item,
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Dashboard", self._on_open_dashboard, default=True), # Set as default (Double Click)
            pystray.MenuItem("Game Mode (Kill AI)", self._on_game_mode),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_exit)
        )

    def _on_open_dashboard(self, icon=None, item=None):
        """Opens the Unified Main Window."""
        logger.info("Open Dashboard selected from tray menu.")
        self.app_instance.main_window.after(0, self.app_instance.show_main_window)

    def _on_game_mode(self, icon=None, item=None):
        logger.info("Game Mode selected from tray menu.")
        activate_game_mode() 

    def _on_exit(self, icon=None, item=None):
        logger.info("Exit selected from tray menu.")
        self.app_instance.stop() 

    def update_status_loop(self):
        while self.should_run:
            new_status_message = self.app_instance.get_overall_status() 
            
            if new_status_message != self.current_status_message:
                self.current_status_message = new_status_message
                
                should_notify = False
                if self.last_status_message is None:
                    should_notify = True
                elif "Idle" in self.last_status_message and "Idle" not in new_status_message:
                    should_notify = True 
                elif "Error" in new_status_message and "Error" not in self.last_status_message:
                    should_notify = True
                
                if should_notify:
                    self.icon.notify(new_status_message)
                
                self.last_status_message = new_status_message

            if self.icon:
                # Update icon visual and tooltip
                self.icon.icon = self.create_icon_image(self.current_status_message)
                self.icon.title = f"LMM: {self.current_status_message}"
                self.icon.menu = self.create_menu()
            
            time.sleep(self.app_instance.polling_interval) 

    def run(self):
        self.icon = pystray.Icon(
            "lmm-monitor", 
            self.create_icon_image(self.current_status_message),
            f"LMM: {self.current_status_message}", 
            menu=self.create_menu()
        )

        update_thread = threading.Thread(target=self.update_status_loop, daemon=True)
        update_thread.start()

        self.icon.run()

    def stop(self):
        self.should_run = False
        if self.icon:
            self.icon.stop()
            logger.info("System tray icon stopped.")
