# utils/config.py
import os
import json
import logging

logger = logging.getLogger('LMM')

class ConfigManager:
    """
    Manages application settings, including loading from and saving to a JSON file.
    """

    DEFAULT_API_HOST = "localhost"
    DEFAULT_API_PORT = "11434"

    def __init__(self, app_name: str = "LMM"):
        self.app_name = app_name
        self.settings_file = os.path.join(
            os.getenv('APPDATA'),
            self.app_name,
            'settings.json'
        )
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        """Load application settings from JSON file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
                    logger.info("Settings loaded successfully")
                    
                    # Ensure default values are present for new settings
                    self._apply_defaults()

                    # Convert old settings format if needed (from OllamaMonitor)
                    if 'api_host' in self.settings and 'api_port' in self.settings:
                        host = self.settings.pop('api_host')
                        port = self.settings.pop('api_port')
                        self.settings['api_url'] = f'http://{host}:{port}'
                        self.save_settings()
                        logger.info("Converted old settings format to new URL format")
            else:
                # Default settings
                self._create_default_settings()
                # Save default settings
                self.save_settings()
                logger.info("Created default settings")
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            self._create_default_settings() # Fallback to defaults on error

    def save_settings(self):
        """Save application settings to JSON file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")

    def get(self, key: str, default=None):
        """Get a setting value, with an optional default."""
        return self.settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting value."""
        self.settings[key] = value
        self.save_settings() # Save immediately on set

    def _create_default_settings(self):
        """Initializes settings with default values."""
        self.settings = {
            'startup': False,
            'api_url': f'http://{self.DEFAULT_API_HOST}:{self.DEFAULT_API_PORT}',
            'polling_interval': 1, # Default polling interval in seconds
            'external_models': [ # List of external models to monitor
                {"name": "Handy AI", "process": "handy.exe", "type": "local_gpu"},
                {"name": "Python Script", "process": "python.exe", "type": "local_cpu"}
            ] 
        }

    def _apply_defaults(self):
        """Applies default values for any missing settings."""
        default_settings = {
            'startup': False,
            'api_url': f'http://{self.DEFAULT_API_HOST}:{self.DEFAULT_API_PORT}',
            'polling_interval': 1,
            'external_models': [
                {"name": "Handy AI", "process": "handy.exe", "type": "local_gpu"},
                {"name": "Python Script", "process": "python.exe", "type": "local_cpu"}
            ]
        }
        for key, value in default_settings.items():
            if key not in self.settings:
                self.settings[key] = value
        
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Test cases
    print("--- Testing ConfigManager ---")
    
    # Initialize config
    config = ConfigManager(app_name="LMM_Test")
    print(f"Initial settings: {config.settings}")
    
    # Test getting a value
    startup = config.get('startup')
    print(f"Startup setting: {startup}")
    
    # Test setting a value
    config.set('startup', True)
    print(f"Settings after change: {config.settings}")
    
    # Re-load to ensure persistence
    new_config = ConfigManager(app_name="LMM_Test")
    print(f"Settings after reload: {new_config.settings}")
    assert new_config.get('startup') == True
    
    # Test API URL
    api_url = new_config.get('api_url')
    print(f"API URL: {api_url}")
    new_config.set('api_url', 'http://192.168.1.1:8080')
    print(f"Settings after API URL change: {new_config.settings}")

    # Clean up test file (optional)
    # os.remove(new_config.settings_file)
    # print(f"Cleaned up {new_config.settings_file}")