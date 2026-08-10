import self_evolve
import os
import sandbox_tools

def main():
    print("=================================================================")
    print("STARTING SANDBOX SELF-EVOLUTION EVALUATOR & EXECUTOR DEMO")
    print("=================================================================")
    
    # Define a coding task that is likely to fail initially or that we ask the model to intentionally test
    task = (
        "Write a Python script that calculates the average of a list of numbers. "
        "IMPORTANT: In your first attempt, do NOT check if the list is empty. Simply divide the sum by "
        "the length of the list, and execute this function passing an empty list `[]`. "
        "This will cause a ZeroDivisionError to test our auto-debugging/evaluator pipeline."
    )
    
    filename = "test_average.py"
    
    # Run the self-evolution loop
    result = self_evolve.evolve_code(task, filename=filename, max_retries=3)
    
    print("\n=================================================================")
    print("DEMO RESULTS:")
    print(f"Task solved successfully? {result['success']}")
    print(f"Total attempts needed: {result.get('attempts', 0)}")
    
    if result['success']:
        print("\nFinal Executed Code:")
        print("--------------------")
        print(result['code'])
        print("--------------------")
        print(f"Final Output:\n{result['stdout']}")
    else:
        print(f"Error encountered: {result.get('error', 'Unknown error')}")
        
    print("=================================================================")

if __name__ == "__main__":
    main()
