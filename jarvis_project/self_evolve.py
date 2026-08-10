import ollama
import sandbox_tools

def evolve_code(prompt: str, filename: str = "task_script.py", max_retries: int = 5) -> dict:
    """Active reasoning loop that generates, runs, evaluates, and fixes sandbox code."""
    print(f"\n[EVOLVE] Starting active reasoning for task: {prompt}")
    
    # System instructions telling the model to output markdown blocks
    system_prompt = (
        "You are an expert Python developer. Generate raw Python code to solve the user's task. "
        "Your response MUST contain ONLY the Python code inside a markdown code block (```python ... ```) "
        "and nothing else. Do not include introductory or concluding text."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    for attempt in range(1, max_retries + 1):
        print(f"\n[EVOLVE] Attempt {attempt} of {max_retries}...")
        
        # Query Ollama
        response = ollama.chat(
            model="qwen2.5:3b",
            messages=messages
        )
        content = response["message"]["content"]
        
        # Extract python block
        code = ""
        if "```python" in content:
            code = content.split("```python")[1].split("```")[0].strip()
        elif "```" in content:
            code = content.split("```")[1].split("```")[0].strip()
        else:
            code = content.strip()
            
        print(f"[EVOLVE] Writing generated code to '{filename}'...")
        sandbox_tools.write_sandbox_file(filename, code)
        
        print(f"[EVOLVE] Running script in sandbox...")
        res = sandbox_tools.run_sandbox_code(filename)
        
        if res["success"]:
            print(f"[EVOLVE] Success on attempt {attempt}!")
            print(f"[STDOUT]:\n{res['stdout']}")
            return {
                "success": True,
                "attempts": attempt,
                "code": code,
                "stdout": res["stdout"]
            }
        
        # If it failed, print error and feed it back to Ollama
        print(f"[EVOLVE] Code failed with exit code {res['returncode']}.")
        print(f"[STDERR]:\n{res['stderr']}")
        
        # Append assistant's previous attempt and the error to the message history
        messages.append({"role": "assistant", "content": content})
        error_msg = (
            f"The code failed with return code {res['returncode']}.\n"
            f"--- STDERR ---\n{res['stderr']}\n--------------\n"
            "Identify the error, explain your correction plan, and output the entire corrected "
            "Python script inside a ```python ``` block."
        )
        messages.append({"role": "user", "content": error_msg})
        
    print("[EVOLVE] Failed to solve the task within the retry limit.")
    return {
        "success": False,
        "attempts": max_retries,
        "error": res["stderr"]
    }
