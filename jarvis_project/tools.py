import subprocess
import psutil
import shutil

def open_app(app_name: str) -> str:
    """Launches a Windows application using subprocess.
    
    Args:
        app_name (str): The name of the application to open (e.g., 'notepad', 'calc').
        
    Returns:
        str: Status message indicating success or failure.
    """
    app_name_lower = app_name.lower().strip()
    
    # Map friendly names to actual executables
    app_map = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe"
    }
    
    executable = app_map.get(app_name_lower, app_name_lower)
    
    try:
        # Use subprocess.Popen so it doesn't block the caller
        subprocess.Popen(executable, shell=True)
        return f"Successfully launched {app_name}."
    except Exception as e:
        return f"Failed to launch {app_name}. Error: {str(e)}"

def get_system_stats() -> str:
    """Gets the current CPU, RAM, and GPU usage.
    
    Returns:
        str: System stats information.
    """
    cpu_usage = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    
    gpu_stats = "GPU: Not available or not NVIDIA"
    if shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True
            )
            out = res.stdout.strip().split(',')
            if len(out) >= 2:
                gpu_util = out[0].strip()
                gpu_mem_util = out[1].strip()
                gpu_stats = f"GPU Utilization: {gpu_util}%, GPU Memory utilization: {gpu_mem_util}%"
        except Exception:
            pass
            
    return f"CPU Usage: {cpu_usage}%, RAM Usage: {ram_usage}%, {gpu_stats}"

def run_cmd(command: str) -> str:
    """Executes a PowerShell command and returns the output.
    
    Args:
        command (str): The powershell command to execute.
        
    Returns:
        str: Standard output or standard error from command execution.
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True, text=True, timeout=15
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\nErrors:\n" + result.stderr
        return output.strip() if output.strip() else "[Command executed with no output]"
    except Exception as e:
        return f"Failed to execute command. Error: {str(e)}"

if __name__ == "__main__":
    print("Testing open_app...")
    print(open_app("notepad"))
    
    print("\nTesting get_system_stats...")
    print(get_system_stats())
    
    print("\nTesting run_cmd...")
    print(run_cmd("Get-Date"))
