#!/usr/bin/env python3
"""
Quick test to verify the exact model name
"""
import requests

def test_model_name():
    endpoint = "http://127.0.0.1:1234"
    
    # Test different model names to find the right one
    model_names_to_try = [
        "mistral-small-3.2",
        "mistralai/mistral-small-3.2", 
        "mistral-small",
        "mistral",
        "",  # Some LM Studio setups accept empty model name
        "default"
    ]
    
    for model_name in model_names_to_try:
        print(f"Testing model name: '{model_name}'")
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Hello, respond with just 'OK'"}],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(
                f"{endpoint}/v1/chat/completions",
                json=payload,
                timeout=10
            )
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                print(f"  ✅ SUCCESS! Response: {content}")
                print(f"  ✅ Working model name: '{model_name}'")
                return model_name
            else:
                print(f"  ❌ Error: {response.text[:200]}...")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
        
        print()
    
    print("❌ None of the model names worked!")
    return None

if __name__ == "__main__":
    print("🔍 Finding the correct model name for LM Studio...")
    print("=" * 50)
    working_model = test_model_name()
    
    if working_model is not None:
        print(f"\n🎉 Found working model name: '{working_model}'")
        print(f"Update your config to use: LOCAL_LLM_MODEL = \"{working_model}\"")
    else:
        print("\n💡 Try checking your LM Studio:")
        print("1. Make sure a model is actually loaded")
        print("2. Check the LM Studio logs for the correct model name")
        print("3. Try restarting LM Studio")