import ollama
import tools

# Define tools for Ollama function calling
available_tools = [
    {
        'type': 'function',
        'function': {
            'name': 'open_app',
            'description': 'Launches a Windows application like notepad, calculator, paint, cmd, or powershell.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'app_name': {
                        'type': 'string',
                        'description': 'The name of the application to open.',
                    },
                },
                'required': ['app_name'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_system_stats',
            'description': 'Gets the current system stats including CPU, RAM, and GPU usage.',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'run_cmd',
            'description': 'Executes a PowerShell command and returns the output.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'command': {
                        'type': 'string',
                        'description': 'The PowerShell command to run.',
                    },
                },
                'required': ['command'],
            },
        },
    },
]

def query_jarvis(prompt: str, history: list) -> str:
    """Queries Ollama with qwen2.5:3b using conversation history, prompt, and tool calling.
    
    Args:
        prompt (str): The user message or voice transcription.
        history (list): List of past message dictionaries.
        
    Returns:
        str: Final text response.
    """
    # Prepend system prompt to guide the model's response format
    system_prompt = (
        "You are JARVIS, a helpful local voice assistant. Provide direct, concise, conversational answers. "
        "When explaining things or answering questions, summarize/explain the results directly. "
        "Do NOT output raw scripts, code blocks, commands, loops, or benchmarking code to the user. "
        "Instead, provide the summarized answer or benchmark result directly in natural, spoken language."
    )
    
    messages = []
    if not any(msg.get('role') == 'system' for msg in history):
        messages.append({'role': 'system', 'content': system_prompt})
    messages.extend(history)
    messages.append({'role': 'user', 'content': prompt})
    
    try:
        response = ollama.chat(
            model='qwen2.5:3b',
            messages=messages,
            tools=available_tools
        )
        
        # Check for tool calls
        if hasattr(response.message, 'tool_calls') and response.message.tool_calls:
            # Append model's response outlining tool call intent
            messages.append(response.message)
            
            # Execute tool calls
            for tool_call in response.message.tool_calls:
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments
                
                print(f"[Tool Executed: {function_name}({function_args})]")
                
                tool_output = ""
                if function_name == 'open_app':
                    tool_output = tools.open_app(function_args.get('app_name', ''))
                elif function_name == 'get_system_stats':
                    tool_output = tools.get_system_stats()
                elif function_name == 'run_cmd':
                    tool_output = tools.run_cmd(function_args.get('command', ''))
                
                # Append tool result to messages
                messages.append({
                    'role': 'tool',
                    'content': tool_output,
                })
            
            # Query LLM again with tool output
            second_response = ollama.chat(
                model='qwen2.5:3b',
                messages=messages
            )
            return second_response.message.content
        else:
            return response.message.content
            
    except Exception as e:
        return f"Sorry, I encountered an error communicating with the model: {str(e)}"

if __name__ == "__main__":
    print("Testing query_jarvis with a simple query...")
    # Simple query
    print(query_jarvis("What is 2 + 2?", []))
