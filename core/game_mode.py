# core/game_mode.py
import logging
import psutil
import os
from typing import List

logger = logging.getLogger('LMM')

# List of processes to terminate during Game Mode
# These are common executables for local AI models
DEFAULT_TARGET_AI_PROCESSES = [
    "ollama_llama_server.exe",
    "handy.exe",
    "python.exe", # Generic Python processes
]

def activate_game_mode(target_processes: List[str] = None) -> dict:
    """
    Terminates specified AI-related processes using psutil.
    Safeguards the current process (LMM) from suicide.
    """
    if target_processes is None:
        target_processes = DEFAULT_TARGET_AI_PROCESSES
        
    logger.info(f"Activating Game Mode. Targeting: {target_processes}")
    
    results = {
        'terminated': [],
        'failed': [],
        'not_found': [] 
    }
    
    current_pid = os.getpid()
    
    # Convert targets to lowercase for case-insensitive matching
    targets_lower = {t.lower() for t in target_processes}
    
    # Iterate over all running processes
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['pid'] == current_pid:
                continue # Skip self

            proc_name = proc.info['name']
            if proc_name and proc_name.lower() in targets_lower:
                logger.info(f"Found target process: {proc_name} (PID: {proc.info['pid']})")
                try:
                    proc.terminate()
                    # specific wait could be added here, but might block GUI
                    results['terminated'].append(proc_name)
                    logger.info(f"Terminated: {proc_name}")
                except psutil.NoSuchProcess:
                    pass # Process died race condition
                except psutil.AccessDenied:
                    logger.error(f"Access denied terminating: {proc_name}")
                    results['failed'].append(proc_name)
                except Exception as e:
                    logger.error(f"Error terminating {proc_name}: {e}")
                    results['failed'].append(proc_name)
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if not results['terminated'] and not results['failed']:
        logger.info("No target processes found running.")
        
    logger.info(f"Game Mode complete. Terminated: {len(results['terminated'])}")
    return results

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    activate_game_mode()
