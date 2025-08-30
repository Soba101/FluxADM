#!/usr/bin/env python3
"""
Quick single-call analysis test for faster results
"""
import asyncio
import sys
import os
import requests
import json

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from config import get_settings


async def quick_analysis(document_text: str):
    """Single-call comprehensive analysis for speed"""
    settings = get_settings()
    
    prompt = f"""Analyze this IT change request comprehensively. Respond with JSON only:

{document_text[:2000]}

Required JSON format:
{{
    "category": "emergency|standard|normal|enhancement|infrastructure|security|maintenance|rollback",
    "priority": "low|medium|high|critical",
    "risk_level": "low|medium|high", 
    "risk_score": 1-9,
    "quality_score": 0-100,
    "title": "concise title",
    "description": "brief summary", 
    "affected_systems": ["system1", "system2"],
    "confidence": 0.85,
    "reasoning": "brief explanation",
    "issues": ["issue1", "issue2"],
    "recommendations": ["rec1", "rec2"]
}}

Respond with JSON only, no additional text."""

    payload = {
        "model": settings.LOCAL_LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert IT change analyst. Respond only with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1500,
        "temperature": 0.1,
        "stream": False
    }
    
    try:
        print("🔍 Sending quick analysis request...")
        response = requests.post(
            f"{settings.LOCAL_LLM_ENDPOINT}/v1/chat/completions",
            json=payload,
            timeout=180,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            usage = data.get('usage', {})
            
            print("✅ Quick analysis successful!")
            print(f"Tokens: {usage.get('prompt_tokens', 0)} in, {usage.get('completion_tokens', 0)} out")
            print(f"Response: {content}")
            
            # Try to parse JSON (handle markdown code blocks)
            try:
                # Remove markdown code blocks if present
                clean_content = content.strip()
                if clean_content.startswith("```json"):
                    clean_content = clean_content[7:]
                if clean_content.endswith("```"):
                    clean_content = clean_content[:-3]
                clean_content = clean_content.strip()
                
                parsed = json.loads(clean_content)
                print("\n🎯 Parsed Results:")
                for key, value in parsed.items():
                    print(f"  {key}: {value}")
                return True
            except json.JSONDecodeError as e:
                print(f"⚠️ Response is not valid JSON: {e}")
                print(f"Clean content: {clean_content[:200]}...")
                return False
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


async def main():
    test_doc = """CHANGE REQUEST: Database Performance Optimization

Priority: High
Category: Infrastructure

BUSINESS JUSTIFICATION:
Production database experiencing performance degradation. Query response times increased from 200ms to 2.5 seconds causing user complaints and potential business impact.

TECHNICAL DETAILS:
- Rebuild fragmented indexes on customer and orders tables
- Archive old transaction data (older than 2 years)  
- Update database statistics
- Optimize slow-running queries

AFFECTED SYSTEMS:
- Production SQL Server database
- Customer portal
- Order management system

IMPLEMENTATION PLAN:
1. Schedule maintenance window (Saturday 2-4 AM)
2. Take full database backup
3. Execute index rebuilding scripts
4. Archive old data
5. Monitor performance for 24 hours

ROLLBACK PLAN:
Restore from backup if performance degrades further

RISK ASSESSMENT:
Medium risk - comprehensive backup strategy provides safety net"""

    print("🚀 Quick Analysis Test")
    print("=" * 50)
    
    success = await quick_analysis(test_doc)
    
    if success:
        print("\n🎉 Quick analysis is working!")
        print("This single-call approach should be much faster than the 3-step analysis.")
    else:
        print("\n❌ Quick analysis failed.")


if __name__ == "__main__":
    asyncio.run(main())