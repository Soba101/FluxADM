#!/usr/bin/env python3
"""
Simple test for local LLM without database operations
"""
import asyncio
import sys
import os
import requests

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from config import get_settings


async def test_simple_local_llm():
    """Test the local LLM directly without database operations"""
    print("🧪 Testing Local LLM Direct Integration")
    print("=" * 50)
    
    settings = get_settings()
    
    # Check if local LLM is available
    try:
        response = requests.get(f"{settings.LOCAL_LLM_ENDPOINT}/v1/models", timeout=5)
        if response.status_code != 200:
            print("❌ Local LLM endpoint not available")
            return False
        print("✅ Local LLM endpoint is available")
    except Exception as e:
        print(f"❌ Cannot connect to local LLM: {e}")
        return False
    
    # Test categorization prompt
    test_prompt = """
    Analyze this IT change request and provide a structured categorization in JSON format.
    
    Document Content:
    CHANGE REQUEST: Database Performance Optimization
    
    Priority: High
    Category: Infrastructure
    
    Business Justification:
    Our production database has been experiencing significant performance degradation over the past week.
    Query response times have increased from 200ms to 2.5 seconds on average, causing user complaints
    and potential business impact. We need to optimize database indexes and clean up unused data.
    
    Technical Details:
    - Rebuild fragmented indexes on customer and orders tables
    - Archive old transaction data (older than 2 years)
    - Update database statistics
    - Optimize slow-running queries identified in performance analysis
    
    Please analyze and respond with JSON containing:
    {
        "category": "one of: emergency, standard, normal, enhancement, infrastructure, security, maintenance, rollback",
        "priority": "one of: low, medium, high, critical",
        "title": "clear, concise title for the change",
        "description": "brief summary of what will be changed",
        "affected_systems": ["list", "of", "affected", "systems"],
        "confidence": 0.85,
        "reasoning": "brief explanation of the categorization decision"
    }
    
    Focus on accuracy and be conservative with priority/risk levels.
    Base decisions on ITIL change management best practices.
    """
    
    payload = {
        "model": settings.LOCAL_LLM_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": "You are an expert IT change management analyst with deep knowledge of ITIL processes, risk assessment, and quality management. Provide structured, accurate responses in JSON format when requested."
            },
            {
                "role": "user", 
                "content": test_prompt
            }
        ],
        "max_tokens": settings.AI_MAX_TOKENS,
        "temperature": settings.AI_TEMPERATURE,
        "stream": False
    }
    
    try:
        print("🔍 Sending categorization request to local LLM...")
        response = requests.post(
            f"{settings.LOCAL_LLM_ENDPOINT}/v1/chat/completions",
            json=payload,
            timeout=settings.AI_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"❌ LLM API error: {response.status_code} - {response.text}")
            return False
        
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']
        usage = response_data.get('usage', {})
        
        print("✅ Local LLM response successful!")
        print(f"Model: {response_data.get('model', 'Unknown')}")
        print(f"Input tokens: {usage.get('prompt_tokens', 0)}")
        print(f"Output tokens: {usage.get('completion_tokens', 0)}")
        print(f"Response length: {len(content)} characters")
        print("\n📄 Response:")
        print("-" * 40)
        print(content)
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"❌ LLM request failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Simple Local LLM Test")
    print("Testing direct HTTP calls to LM Studio")
    print("=" * 50)
    
    success = await test_simple_local_llm()
    
    if success:
        print("\n🎉 Local LLM integration is working perfectly!")
        print("\n💡 Next steps:")
        print("   1. The AI processor should work now with the simplified setup")
        print("   2. Database relationship issues won't affect AI processing")
        print("   3. Ready to test full FluxADM application!")
    else:
        print("\n❌ Local LLM test failed. Check LM Studio setup.")


if __name__ == "__main__":
    asyncio.run(main())