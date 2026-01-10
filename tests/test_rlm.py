import requests
import json
import time

def test_recursive_agent():
    print("Generating 'large' corpus...")
    # Create a synthetic log file with 1000 lines
    lines = [f"INFO: {i} - System operating normally." for i in range(500)]
    lines.append("CRITICAL ERROR: The flux capacitor has overheated due to voltage spike.")
    lines.extend([f"INFO: {i} - System operating normally." for i in range(500, 1000)])
    
    corpus = "\n".join(lines)
    
    question = "Analyze the log file. Find the critical error message and then use the 'ask_llm' function to explain how to fix it."

    payload = {
        "question": question,
        "corpus": corpus
    }

    print(f"Sending request to Recursive Agent (Corpus size: {len(corpus)} chars)...")
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:8081/agent/recursive",
            json=payload
        )
        
        print(f"Response received in {time.time() - start_time:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            if not result.get("success", True):
                print(f"Agent Error: {result.get('error')}")
            
            print("\n=== FINAL ANSWER ===")
            print(result["answer"])
            print("\n=== REASONING STEPS ===")
            for step in result["steps"]:
                print(f"\nStep {step['step_number']}:")
                print(f"Thought: {step['thought']}")
                print(f"Action: {step['action']}")
                print(f"Input: {step['action_input']}")
                print(f"Observation: {step['observation']}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_recursive_agent()
