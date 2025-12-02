# core/model_manager.py
import logging
import json
from core.powershell import run_hidden_powershell_cmd

logger = logging.getLogger('LMM')

class OllamaManager:
    """
    Manages interaction with the Ollama CLI for listing, pulling, and deleting models.
    """
    def __init__(self):
        logger.info("OllamaManager initialized.")

    def _execute_ollama_command(self, command: str) -> tuple[int, str]:
        """
        Executes an ollama CLI command and returns its exit code and output.
        """
        full_command = f"ollama {command}"
        logger.debug(f"Executing Ollama command: {full_command}")
        
        # run_hidden_powershell_cmd returns only stdout, without exit code or stderr directly.
        # For better error handling, we might need a more direct subprocess call here,
        # or enhance run_hidden_powershell_cmd to return exit code and stderr.
        # For now, we'll assume successful execution if output is not empty for 'list'
        # and check for specific strings for 'pull'/'rm'.
        output = run_hidden_powershell_cmd(full_command)
        
        # A more robust solution for subprocess.run returning exit code and stderr would be ideal.
        # For simplicity, we'll assume 0 for success and -1 for generic failure
        # and rely on parsing output for specific error messages.
        
        if "Error" in output or "failed" in output.lower():
            logger.error(f"Ollama command '{command}' failed: {output}")
            return -1, output
        
        logger.info(f"Ollama command '{command}' executed successfully.")
        return 0, output

    def list_models(self) -> list[dict]:
        """
        Lists installed Ollama models.
        Returns a list of dictionaries, each representing a model.
        """
        exit_code, output = self._execute_ollama_command("list")
        models = []
        if exit_code == 0 and output:
            # Parse the output of 'ollama list'
            # Example output:
            # NAME                     ID             SIZE    MODIFIED
            # llama2:latest            f075d2f2        3.8 GB  3 weeks ago
            # mistral:latest           f8909d94       4.1 GB  3 weeks ago
            lines = output.strip().split('\n')
            if len(lines) > 1: # Skip header line
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        models.append({
                            "name": parts[0],
                            "id": parts[1],
                            "size": parts[2],
                            "modified": " ".join(parts[3:])
                        })
        return models

    def pull_model(self, model_name: str) -> bool:
        """
        Pulls (downloads and installs) an Ollama model.
        """
        logger.info(f"Attempting to pull Ollama model: {model_name}")
        exit_code, output = self._execute_ollama_command(f"pull {model_name}")
        if exit_code == 0:
            logger.info(f"Successfully initiated pull for model: {model_name}. Output: {output}")
            return True
        else:
            logger.error(f"Failed to pull model: {model_name}. Output: {output}")
            return False

    def delete_model(self, model_name: str) -> bool:
        """
        Deletes an Ollama model.
        """
        logger.info(f"Attempting to delete Ollama model: {model_name}")
        # Ollama rm command requires confirmation.
        # We need to force it with --force or simulate 'y' input.
        # For CLI interaction, --force is usually preferred in scripts.
        exit_code, output = self._execute_ollama_command(f"rm --force {model_name}")
        if exit_code == 0:
            logger.info(f"Successfully deleted model: {model_name}. Output: {output}")
            return True
        else:
            logger.error(f"Failed to delete model: {model_name}. Output: {output}")
            return False

if __name__ == "__main__":
    # Basic test for OllamaManager
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    manager = OllamaManager()
    
    print("\n--- Listing Models ---")
    models = manager.list_models()
    if models:
        for model in models:
            print(model)
    else:
        print("No Ollama models found or Ollama is not running.")

    # Example of pulling and deleting (uncomment to test)
    # print("\n--- Pulling a Model (e.g., 'tinyllama') ---")
    # if manager.pull_model("tinyllama"):
    #     print("TinyLlama pull command sent. Check Ollama status for progress.")
    # else:
    #     print("Failed to initiate TinyLlama pull.")

    # print("\n--- Deleting a Model (e.g., 'tinyllama') ---")
    # if manager.delete_model("tinyllama"):
    #     print("TinyLlama delete command sent.")
    # else:
    #     print("Failed to delete TinyLlama.")
    
    # print("\n--- Listing Models After Operations ---")
    # models = manager.list_models()
    # if models:
    #     for model in models:
    #         print(model)
    # else:
    #     print("No Ollama models found or Ollama is not running.")
