import os
import subprocess
import sys

SANDBOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox")

def _sanitize_path(filename: str) -> str:
    """Ensures file operations remain strictly inside the sandbox directory."""
    # Strip any directory pathing and just use the base filename
    base_name = os.path.basename(filename)
    target_path = os.path.abspath(os.path.join(SANDBOX_DIR, base_name))
    if not target_path.startswith(os.path.abspath(SANDBOX_DIR)):
        raise ValueError("Access denied: File operations must remain strictly inside the sandbox directory.")
    return target_path


def write_sandbox_file(filename: str, content: str) -> str:
    """Writes content to a file inside the sandbox directory."""
    path = _sanitize_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully wrote {filename} in sandbox."


def read_sandbox_file(filename: str) -> str:
    """Reads the content of a file inside the sandbox directory."""
    path = _sanitize_path(filename)
    if not os.path.exists(path):
        return f"Error: File {filename} does not exist in sandbox."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_sandbox_code(filename: str) -> dict:
    """Executes a Python script inside the sandbox and returns execution results."""
    path = _sanitize_path(filename)
    if not os.path.exists(path):
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Error: File {filename} not found."
        }
    
    # Use the active virtual environment's python if available
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    
    try:
        # Run command in sandbox directory as working directory
        result = subprocess.run(
            [python_exe, path],
            capture_output=True,
            text=True,
            cwd=SANDBOX_DIR,
            timeout=15
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -2,
            "stdout": "",
            "stderr": "Error: Execution timed out (15s limit exceeded)."
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -3,
            "stdout": "",
            "stderr": f"Execution error: {str(e)}"
        }
