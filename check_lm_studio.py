#!/usr/bin/env python3
"""
Check what models are available in LM Studio
"""
import requests
import json

def check_lm_studio():
    """Check LM Studio endpoint and available models"""
    endpoint = "http://127.0.0.1:1234"
    
    print("🔍 Checking LM Studio endpoint...")
    
    try:
        # Check models endpoint
        response = requests.get(f"{endpoint}/v1/models", timeout=10)
        
        if response.status_code == 200:
            models_data = response.json()
            print("✅ LM Studio is running and responding")
            print("\n📋 Available models:")
            print("-" * 40)
            
            if 'data' in models_data:
                for model in models_data['data']:
                    print(f"ID: {model.get('id', 'Unknown')}")
                    print(f"Object: {model.get('object', 'Unknown')}")
                    if 'owned_by' in model:
                        print(f"Owned by: {model['owned_by']}")
                    print("-" * 40)
            else:
                print("No models found in response")
                print("Raw response:")
                print(json.dumps(models_data, indent=2))
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        print("Make sure LM Studio is running on http://127.0.0.1:1234")

    # Also try to check if there's a loaded model by testing completion
    try:
        print("\n🧪 Testing chat completions endpoint...")
        test_payload = {
            "model": "any",  # Some endpoints accept any model name
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{endpoint}/v1/chat/completions",
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Chat completions endpoint is working")
            data = response.json()
            if 'model' in data:
                print(f"Detected model: {data['model']}")
        else:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Chat completions test failed: {e}")

if __name__ == "__main__":
    check_lm_studio()