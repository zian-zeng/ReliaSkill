import time
from autoskill.local_model import LocalHFChatRunner

def main():
    print("Initializing Qwen/Qwen2.5-7B-Instruct in 4-bit...")
    start_time = time.time()
    
    try:
        runner = LocalHFChatRunner(
            model_name_or_path="Qwen/Qwen2.5-7B-Instruct",
            device_map="auto",
            load_in_4bit=True,
            max_new_tokens=100
        )
        
        print("Model object created. Starting first inference to trigger load...")
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, can you hear me? What is 2+2?"}
        ]
        
        response = runner.generate_chat(messages=messages, temperature=0.0)
        
        print(f"\n--- SUCCESS ---")
        print(f"Time taken: {time.time() - start_time:.2f} seconds")
        print(f"Model Response: {response}")
        
    except Exception as e:
        print(f"\n--- ERROR ---")
        print(f"Exception during model load/inference: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
