#!/usr/bin/env python3
"""
Helper functions for batch document processing
"""
import streamlit as st
import asyncio
import uuid


def process_single_file(file_handler, ai_processor, uploaded_file, title="", description=""):
    """Process a single file and return results"""
    try:
        # Get file data
        file_data = uploaded_file.read()
        filename = uploaded_file.name
        
        # Validate file
        is_valid, error_msg = file_handler.validate_file(file_data, filename)
        if not is_valid:
            return {"success": False, "error": f"Validation failed: {error_msg}", "filename": filename}
        
        # Save file
        file_path, save_error = file_handler.save_file(file_data, filename)
        if save_error:
            return {"success": False, "error": f"Save failed: {save_error}", "filename": filename}
        
        # Extract text
        extracted_text, extract_error, metadata = file_handler.extract_text(file_path)
        if extract_error:
            return {"success": False, "error": f"Text extraction failed: {extract_error}", "filename": filename}
        
        if not extracted_text or len(extracted_text.strip()) < 50:
            return {"success": False, "error": "Very little text extracted", "filename": filename}
        
        # AI Analysis (only if LLM is available)
        if ai_processor.local_llm_available:
            try:
                test_cr_id = str(uuid.uuid4())
                
                # Use asyncio to run the async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    analysis_result = loop.run_until_complete(
                        ai_processor.analyze_change_request(test_cr_id, extracted_text)
                    )
                finally:
                    loop.close()
                
                return {
                    "success": True,
                    "filename": filename,
                    "extracted_text": extracted_text,
                    "metadata": metadata,
                    "analysis_result": analysis_result,
                    "file_data": file_data
                }
            except Exception as ai_error:
                return {
                    "success": True,  # File processed, just AI failed
                    "filename": filename,
                    "extracted_text": extracted_text,
                    "metadata": metadata,
                    "analysis_result": None,
                    "ai_error": str(ai_error),
                    "file_data": file_data
                }
        else:
            return {
                "success": True,
                "filename": filename,
                "extracted_text": extracted_text,
                "metadata": metadata,
                "analysis_result": None,
                "ai_error": "Local LLM not available",
                "file_data": file_data
            }
            
    except Exception as e:
        return {"success": False, "error": str(e), "filename": uploaded_file.name}


def display_batch_results(results, save_change_request_func, title="", description=""):
    """Display batch processing results"""
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Files", len(results))
    with col2:
        st.metric("Successful", len(successful))
    with col3:
        st.metric("Failed", len(failed))
    
    # Failed files
    if failed:
        st.error("❌ Failed Files:")
        for result in failed:
            st.write(f"• **{result['filename']}**: {result['error']}")
    
    # Successful files
    if successful:
        st.success("✅ Successfully Processed Files:")
        
        created_crs = []
        for result in successful:
            st.write(f"📄 **{result['filename']}**")
            
            if result.get("analysis_result"):
                # Display AI analysis
                analysis = result["analysis_result"]
                cat = analysis.get('categorization', {})
                risk = analysis.get('risk_assessment', {})
                quality = analysis.get('quality_check', {})
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Category", cat.get('category', 'Unknown').title())
                with col2:
                    st.metric("Priority", cat.get('priority', 'Unknown').title())
                with col3:
                    st.metric("Risk", risk.get('risk_level', 'Unknown').title())
                with col4:
                    st.metric("Quality", f"{quality.get('quality_score', 0)}%")
                
                # Save to database
                saved_cr = save_change_request_func(
                    result["analysis_result"], 
                    result["filename"], 
                    result["extracted_text"], 
                    title, 
                    description
                )
                
                if saved_cr:
                    st.info(f"🎯 Created Change Request: **{saved_cr.cr_number}**")
                    created_crs.append(saved_cr)
                else:
                    st.warning("⚠️ Could not save to database")
            else:
                # No AI analysis
                error_msg = result.get("ai_error", "No analysis available")
                st.warning(f"⚠️ AI Analysis failed: {error_msg}")
                st.info(f"Text extracted: {len(result['extracted_text'])} characters")
            
            st.divider()
        
        if created_crs:
            st.success(f"🎉 Successfully created {len(created_crs)} Change Request{'s' if len(created_crs) > 1 else ''}!")
            
            # Show CR numbers
            cr_numbers = [cr.cr_number for cr in created_crs]
            st.info("**Created Change Requests**: " + ", ".join(cr_numbers))