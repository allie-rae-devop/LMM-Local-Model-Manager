# core/hardware.py
import logging
import psutil

try:
    # Correct import for nvidia-ml-py
    import pynvml
    _nvml_available = True
except ImportError:
    _nvml_available = False
    logging.warning("nvidia-ml-py (pynvml) not installed. GPU monitoring will be disabled.")
except Exception as error: # Catch generic exception during import/init
    _nvml_available = False
    logging.warning(f"Failed to import pynvml: {error}. GPU monitoring will be disabled.")

class HardwareMonitor:
    def __init__(self):
        self.logger = logging.getLogger('LMM')
        self.nvml_initialized = False
        if _nvml_available:
            try:
                pynvml.nvmlInit()
                self.nvml_initialized = True
                self.device_count = pynvml.nvmlDeviceGetCount()
                self.logger.info(f"NVML initialized. Found {self.device_count} NVIDIA GPUs.")
            except pynvml.NVMLError as error:
                self.logger.error(f"Failed to initialize NVML: {error}. GPU monitoring disabled.")
                self.nvml_initialized = False
        else:
            self.logger.warning("pynvml not available. GPU monitoring disabled.")

    def get_gpu_processes(self) -> list[dict]:
        """
        Retrieves a list of processes currently using the GPU.
        """
        processes = []
        if not self.nvml_initialized:
            return processes

        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # Helper to add process
            def add_procs(procs, type_name):
                for proc in procs:
                    if any(p['pid'] == proc.pid for p in processes): continue
                    try:
                        p_obj = psutil.Process(proc.pid)
                        name = p_obj.name()
                        # Try to get command line for python/powershell to be more specific
                        if name.lower() in ['python.exe', 'powershell.exe', 'pwsh.exe', 'cmd.exe']:
                            try:
                                cmdline = p_obj.cmdline()
                                if len(cmdline) > 1:
                                    # Use the script name or first arg
                                    name = f"{name} ({cmdline[1]})"
                            except: pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        name = "Unknown"
                    
                    processes.append({
                        "pid": proc.pid,
                        "name": name,
                        "vram_used_mb": int(proc.usedGpuMemory / (1024**2)) if proc.usedGpuMemory else 0,
                        "type": type_name
                    })

            try:
                add_procs(pynvml.nvmlDeviceGetComputeRunningProcesses(handle), "Compute")
            except pynvml.NVMLError: pass

            try:
                add_procs(pynvml.nvmlDeviceGetGraphicsRunningProcesses(handle), "Graphics")
            except pynvml.NVMLError: pass

        except Exception as e:
            self.logger.error(f"Error getting GPU processes: {e}")

        return processes

    def get_gpu_info(self) -> dict:
        """
        Retrieves GPU information including Temp and decoded Name.
        """
        info = {
            "vram_total": "N/A",
            "vram_used": "N/A",
            "vram_free": "N/A",
            "gpu_utilization": "N/A",
            "temperature": "N/A",
            "name": "N/A",
            "processes": []
        }

        if not self.nvml_initialized:
            return info

        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # Name - Decode bytes if necessary
            raw_name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(raw_name, bytes):
                info["name"] = raw_name.decode('utf-8')
            else:
                info["name"] = raw_name

            # Memory
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info["vram_total"] = f"{mem_info.total / (1024**3):.2f} GB"
            info["vram_used"] = f"{mem_info.used / (1024**3):.2f} GB"
            info["vram_free"] = f"{mem_info.free / (1024**3):.2f} GB"

            # Utilization
            try:
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                info["gpu_utilization"] = f"{utilization.gpu}%"
            except pynvml.NVMLError:
                info["gpu_utilization"] = "N/A"

            # Temperature
            try:
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMP_GPU)
                info["temperature"] = f"{temp} C"
            except pynvml.NVMLError:
                info["temperature"] = "N/A"

            # Processes
            info["processes"] = self.get_gpu_processes()

        except Exception as e:
            self.logger.error(f"Unexpected error in get_gpu_info: {e}")
        
        return info

    def __del__(self):
        if self.nvml_initialized:
            try:
                pynvml.nvmlShutdown()
            except: pass