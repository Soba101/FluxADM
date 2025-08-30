#!/usr/bin/env python3
"""
Test script for local LLM integration with FluxADM
Tests the Mistral model via LM Studio endpoint
"""
import asyncio
import sys
import os

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from app.services.ai_processor import AIProcessor


async def test_local_llm():
    """Test the local LLM integration"""
    print("🧪 Testing FluxADM Local LLM Integration")
    print("=" * 50)
    
    # Initialize AI processor
    try:
        ai_processor = AIProcessor()
        print("✅ AI Processor initialized successfully")
        
        # Check if local LLM is available
        if not ai_processor.local_llm_available:
            print("❌ Local LLM endpoint not available at http://127.0.0.1:1234")
            print("   Make sure LM Studio is running with the Mistral model loaded")
            return False
        
        print("✅ Local LLM endpoint is available")
        
    except Exception as e:
        print(f"❌ Failed to initialize AI processor: {e}")
        return False
    
    # Test document content (sample change request)
    test_document = """
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
    
    Implementation Plan:
    1. Schedule maintenance window during low usage (2-4 AM)
    2. Take full database backup before changes
    3. Execute index rebuilding scripts
    4. Archive old data to separate database
    5. Update statistics and test query performance
    6. Monitor system performance for 24 hours post-implementation
    
    Rollback Plan:
    Restore from backup if performance degrades further or system becomes unstable.
    
    Risk Assessment:
    Medium risk - Database maintenance during low-usage window minimizes impact.
    Comprehensive backup strategy provides safety net.
    """
    
    print("\n🔍 Testing Change Request Analysis...")
    print(f"Document length: {len(test_document)} characters")
    
    try:
        # Test the full CR analysis
        result = await ai_processor.analyze_change_request(
            cr_id="test-cr-001",
            document_content=test_document
        )
        
        print("\n✅ Analysis completed successfully!")
        print("\n📊 Results:")
        print("-" * 30)
        
        # Display categorization results
        if 'categorization' in result:
            cat = result['categorization']
            print(f"Category: {cat.get('category', 'N/A')}")
            print(f"Priority: {cat.get('priority', 'N/A')}")
            print(f"Title: {cat.get('title', 'N/A')}")
            print(f"Confidence: {cat.get('confidence', 'N/A')}")
        
        # Display risk assessment
        if 'risk_assessment' in result:
            risk = result['risk_assessment']
            print(f"Risk Level: {risk.get('risk_level', 'N/A')}")
            print(f"Risk Score: {risk.get('risk_score', 'N/A')}")
        
        # Display quality check
        if 'quality_check' in result:
            quality = result['quality_check']
            print(f"Quality Score: {quality.get('quality_score', 'N/A')}")
            print(f"Issues Found: {len(quality.get('issues', []))}")
        
        print(f"\nOverall Confidence: {result.get('overall_confidence', 'N/A')}")
        print(f"Providers Used: {result.get('providers_used', [])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False


async def test_simple_prompt():
    """Test a simple prompt to verify basic connectivity"""
    print("\n🧪 Testing Simple Prompt...")
    
    try:
        ai_processor = AIProcessor()
        
        # Test with a simple categorization prompt
        prompt = ai_processor._build_categorization_prompt("Test change request for database optimization")
        
        result = await ai_processor._call_local_llm(prompt, ai_processor.settings.LOCAL_LLM_MODEL)
        
        print("✅ Simple prompt test successful!")
        print(f"Response length: {len(result['response'])} characters")
        print(f"Model used: {result['model']}")
        print(f"Provider: {result['provider']}")
        print(f"Tokens: {result['input_tokens']} in, {result['output_tokens']} out")
        
        # Show first 200 characters of response
        response_preview = result['response'][:200]
        print(f"\nResponse preview:\n{response_preview}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple prompt test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 FluxADM Local LLM Test Suite")
    print("Testing Mistral Small 3.2 24B via LM Studio")
    print("=" * 60)
    
    # Test 1: Simple connectivity and prompt
    success1 = await test_simple_prompt()
    
    if success1:
        print("\n" + "=" * 60)
        # Test 2: Full document analysis
        success2 = await test_local_llm()
        
        if success2:
            print("\n" + "=" * 60)
            print("🎉 All tests passed! Local LLM integration is working.")
            print("\n💡 Next steps:")
            print("   1. Start FluxADM: python3 start_fluxadm.py")
            print("   2. Upload documents via Streamlit dashboard")
            print("   3. Watch AI analysis results in real-time")
        else:
            print("\n⚠️  Basic connectivity works, but document analysis failed.")
    else:
        print("\n❌ Basic connectivity test failed. Check LM Studio setup.")


if __name__ == "__main__":
    asyncio.run(main())