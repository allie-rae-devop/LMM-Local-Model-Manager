# core/powershell.py
import subprocess
import logging

logger = logging.getLogger('LMM')

def run_hidden_powershell_cmd(command: str):
    """
    Runs a PowerShell command hidden, without a new window.
    """
    creation_flags = 0x08000000 # CREATE_NO_WINDOW
    try:
        # Use subprocess.run for better control and error handling
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            creationflags=creation_flags,
            capture_output=True,
            text=True,
            check=False # Do not raise an exception for non-zero exit codes immediately
        )
        if result.returncode != 0:
            logger.error(f"PowerShell command failed with exit code {result.returncode}: {command}\nError: {result.stderr.strip()}")
        elif result.stderr:
            logger.warning(f"PowerShell command had stderr output: {command}\nWarning: {result.stderr.strip()}")
        else:
            logger.info(f"PowerShell command executed successfully: {command}")
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Error executing PowerShell command: {e}")
        return ""