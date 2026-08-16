import os

code = """
import psutil
try:
    import pynvml
    pynvml.nvmlInit()
    HAS_NVML = True
except Exception:
    HAS_NVML = False

def get_full_system_overview() -> str:
    \"\"\"Gathers real-time telemetry for CPU, RAM, GPU, storage partitions, and network I/O.\"\"\"
    lines = ["=== FULL SYSTEM TELEMETRY ==="]

    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)
    lines.append(f"CPU Utilization: {cpu_percent}% ({psutil.cpu_count(logical=True)} Cores)")

    # RAM
    ram = psutil.virtual_memory()
    lines.append(f"System RAM: {ram.used / (1024**3):.2f} GB / {ram.total / (1024**3):.2f} GB ({ram.percent}% used)")

    # GPU
    if HAS_NVML:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            gpu_name = pynvml.nvmlDeviceGetName(handle)
            gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
            gpu_mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            lines.append(f"GPU ({gpu_name}): {gpu_util}% Load | VRAM: {gpu_mem.used / (1024**3):.2f} / {gpu_mem.total / (1024**3):.2f} GB | Temp: {gpu_temp}°C")
        except Exception as e:
            lines.append(f"GPU Telemetry Error: {str(e)}")

    # Storage
    lines.append("\\n--- Storage ---")
    for part in psutil.disk_partitions(all=False):
        if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''): continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            lines.append(f"Drive {part.mountpoint}: {usage.free / (1024**3):.1f} GB free of {usage.total / (1024**3):.1f} GB ({usage.percent}% full)")
        except Exception: continue

    return "\\n".join(lines)

def get_top_resource_hogs(limit: int = 5) -> str:
    \"\"\"Identifies the processes consuming the most CPU and RAM.\"\"\"
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try: procs.append(p.info)
        except Exception: continue

    top_cpu = sorted(procs, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:limit]
    top_ram = sorted(procs, key=lambda x: x['memory_percent'] or 0, reverse=True)[:limit]

    output = ["=== TOP PROCESSES ===", "\\nTop CPU:"]
    for p in top_cpu: output.append(f"  - {p['name']} (PID {p['pid']}): {p['cpu_percent']}%")
    output.append("\\nTop RAM:")
    for p in top_ram: output.append(f"  - {p['name']} (PID {p['pid']}): {p['memory_percent']:.1f}%")
    
    return "\\n".join(output)

def analyze_windows_storage(drive_letter: str = "C:") -> str:
    \"\"\"Scans for massive Windows system files (hiberfil, pagefile) and Temp folders.\"\"\"
    drive_root = f"{drive_letter}\\"
    lines = [f"=== STORAGE ANALYSIS FOR {drive_letter} ==="]
    
    for fname in ["hiberfil.sys", "pagefile.sys", "swapfile.sys"]:
        fpath = os.path.join(drive_root, fname)
        if os.path.exists(fpath):
            try: lines.append(f"  - {fname}: {os.path.getsize(fpath) / (1024**3):.2f} GB")
            except Exception: lines.append(f"  - {fname}: [Locked/In Use]")

    temp_dirs = [os.getenv("TEMP"), os.path.join(drive_root, "Windows", "Temp")]
    lines.append("\\nTemp Folders:")
    for tdir in filter(None, temp_dirs):
        if os.path.exists(tdir):
            try:
                total_size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(tdir) for f in fs)
                lines.append(f"  - {tdir}: {total_size / (1024**2):.1f} MB")
            except Exception: lines.append(f"  - {tdir}: [Access Denied]")
            
    return "\\n".join(lines)

def execute_admin_fix(command: str) -> str:
    \"\"\"Safely prompts the user before executing shell cleanup commands.\"\"\"
    print(f"\\n[SYSTEM ACTION PROPOSED]\\nCommand: {command}")
    if input("Execute this command? (y/n): ").strip().lower() == 'y':
        try:
            import subprocess
            res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
            return f"Success:\\n{res.stdout}\\nErrors:\\n{res.stderr}"
        except Exception as e: return f"Execution failed: {str(e)}"
    return "Cancelled by user."
"""

with open(r"m:\coding\Jarvis\jarvis_project\tools.py", "a", encoding="utf-8") as f:
    f.write("\n" + code + "\n")

print("Done appending to tools.py")
