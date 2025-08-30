"""
AI Processing Service - Core AI analysis functionality for FluxADM
Supports multiple AI providers with fallback strategies
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog
import requests

# Local LLM only - no external AI service dependencies

from config import get_settings, get_ai_config
from app.models import db, AIAnalysisResult, ChangeRequest
from app.models.change_request import ChangeRequestCategory, ChangeRequestPriority, ChangeRequestRisk

logger = structlog.get_logger(__name__)


class AIProcessor:
    """
    Multi-provider AI processing service with fallback strategies
    Handles document analysis, risk assessment, and quality checking
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_config = get_ai_config()
        self._initialize_clients()
        
    def _initialize_clients(self):
        """Initialize local LLM client only"""
        self.local_llm_available = False
        
        # Check local LLM availability
        try:
            response = requests.get(f"{self.settings.LOCAL_LLM_ENDPOINT}/v1/models", timeout=5)
            if response.status_code == 200:
                self.local_llm_available = True
                logger.info("Local LLM endpoint available", endpoint=self.settings.LOCAL_LLM_ENDPOINT)
        except Exception as e:
            logger.warning("Local LLM endpoint not available", error=str(e))
    
    async def analyze_change_request(self, cr_id: str, document_content: str) -> Dict[str, Any]:
        """
        Comprehensive CR analysis using AI with multiple providers
        
        Args:
            cr_id: Change request UUID
            document_content: Raw text content from CR document
            
        Returns:
            Dictionary containing structured analysis results
        """
        logger.info("Starting CR analysis", cr_id=cr_id, content_length=len(document_content))
        
        analysis_results = {}
        
        try:
            # Perform different types of analysis
            categorization_result = await self._analyze_categorization(cr_id, document_content)
            risk_assessment_result = await self._analyze_risk_assessment(cr_id, document_content)
            quality_check_result = await self._analyze_quality_check(cr_id, document_content)
            
            # Combine results
            analysis_results = {
                'categorization': categorization_result,
                'risk_assessment': risk_assessment_result,
                'quality_check': quality_check_result,
                'overall_confidence': self._calculate_overall_confidence([
                    categorization_result,
                    risk_assessment_result,
                    quality_check_result
                ]),
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'providers_used': self._get_providers_used([
                    categorization_result,
                    risk_assessment_result,
                    quality_check_result
                ])
            }
            
            logger.info("CR analysis completed successfully", 
                       cr_id=cr_id, 
                       confidence=analysis_results['overall_confidence'])
            
        except Exception as e:
            logger.error("CR analysis failed", cr_id=cr_id, error=str(e))
            # Return fallback analysis
            analysis_results = await self._fallback_analysis(cr_id, document_content)
        
        return analysis_results
    
    async def _analyze_categorization(self, cr_id: str, content: str) -> Dict[str, Any]:
        """Analyze and categorize the change request"""
        
        prompt = self._build_categorization_prompt(content)
        
        # Try primary AI service
        try:
            result = await self._call_ai_service(
                prompt=prompt,
                analysis_type="categorization",
                cr_id=cr_id,
                service_preference="primary"
            )
            
            return self._parse_categorization_response(result)
            
        except Exception as e:
            logger.warning("Primary categorization failed, trying fallback", 
                         cr_id=cr_id, error=str(e))
            
            # Try fallback service
            try:
                result = await self._call_ai_service(
                    prompt=prompt,
                    analysis_type="categorization", 
                    cr_id=cr_id,
                    service_preference="fallback"
                )
                
                return self._parse_categorization_response(result)
                
            except Exception as fallback_error:
                logger.error("Fallback categorization also failed", 
                           cr_id=cr_id, error=str(fallback_error))
                
                # Use rule-based fallback
                return self._rule_based_categorization(content)
    
    async def _analyze_risk_assessment(self, cr_id: str, content: str) -> Dict[str, Any]:
        """Perform AI-powered risk assessment"""
        
        prompt = self._build_risk_assessment_prompt(content)
        
        try:
            result = await self._call_ai_service(
                prompt=prompt,
                analysis_type="risk_assessment",
                cr_id=cr_id
            )
            
            return self._parse_risk_assessment_response(result)
            
        except Exception as e:
            logger.error("Risk assessment failed", cr_id=cr_id, error=str(e))
            return self._rule_based_risk_assessment(content)
    
    async def _analyze_quality_check(self, cr_id: str, content: str) -> Dict[str, Any]:
        """Perform quality analysis and issue detection"""
        
        prompt = self._build_quality_check_prompt(content)
        
        try:
            result = await self._call_ai_service(
                prompt=prompt,
                analysis_type="quality_check",
                cr_id=cr_id
            )
            
            return self._parse_quality_check_response(result)
            
        except Exception as e:
            logger.error("Quality check failed", cr_id=cr_id, error=str(e))
            return self._rule_based_quality_check(content)
    
    async def _call_ai_service(self, prompt: str, analysis_type: str, cr_id: str, 
                              service_preference: str = "primary") -> Dict[str, Any]:
        """
        Call AI service with retry logic and error handling
        """
        start_time = time.time()
        
        # Use local LLM only
        if self.local_llm_available:
            service_name = "local"
            model = self.settings.LOCAL_LLM_MODEL
        else:
            raise Exception("Local LLM not available")
        
        # Make API call with retries
        max_retries = self.settings.AI_MAX_RETRIES
        
        for attempt in range(max_retries + 1):
            try:
                if service_name == "local":
                    result = await self._call_local_llm(prompt, model)
                else:
                    raise Exception(f"Unknown service: {service_name}")
                
                processing_time = int((time.time() - start_time) * 1000)
                
                # Record successful analysis (skip database save for standalone mode)
                try:
                    analysis_record = AIAnalysisResult(
                        cr_id=cr_id,
                        analysis_type=analysis_type,
                        ai_model_used=model,
                        provider=service_name,
                        processing_time_ms=processing_time,
                        confidence_score=result.get('confidence', 0.8),
                        raw_response=result,
                        structured_result=result,
                        input_tokens=result.get('input_tokens', 0),
                        output_tokens=result.get('output_tokens', 0)
                    )
                    
                    db.session.add(analysis_record)
                    db.session.commit()
                    logger.info("Analysis record saved to database")
                except Exception as db_error:
                    logger.warning("Failed to save analysis to database", error=str(db_error))
                    # Continue without database save - this allows standalone analysis
                
                logger.info("AI service call successful",
                           service=service_name,
                           model=model,
                           processing_time_ms=processing_time,
                           attempt=attempt + 1)
                
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt)  # Exponential backoff
                    logger.warning("AI service call failed, retrying",
                                 service=service_name,
                                 attempt=attempt + 1,
                                 error=str(e),
                                 wait_time=wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("AI service call failed after all retries",
                               service=service_name,
                               max_retries=max_retries,
                               error=str(e))
                    
                    # Record failed analysis (skip database save for standalone mode)
                    try:
                        analysis_record = AIAnalysisResult(
                            cr_id=cr_id,
                            analysis_type=analysis_type,
                            ai_model_used=model,
                            provider=service_name,
                            processing_time_ms=int((time.time() - start_time) * 1000),
                            confidence_score=0.0,
                            error_occurred='true',
                            error_message=str(e),
                            retry_count=attempt + 1
                        )
                        
                        db.session.add(analysis_record)
                        db.session.commit()
                    except Exception as db_error:
                        logger.warning("Failed to save error analysis to database", error=str(db_error))
                    
                    raise e
    
    # External AI services removed - using local LLM only
    
    async def _call_local_llm(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call local LLM via LM Studio endpoint"""
        
        if not self.local_llm_available:
            raise Exception("Local LLM endpoint not available")
        
        # Prepare the request payload for OpenAI-compatible endpoint
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert IT change management analyst with deep knowledge of ITIL processes, risk assessment, and quality management. Provide structured, accurate responses in JSON format when requested."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": self.settings.AI_MAX_TOKENS,
            "temperature": self.settings.AI_TEMPERATURE,
            "stream": False
        }
        
        # Make the API call
        response = requests.post(
            f"{self.settings.LOCAL_LLM_ENDPOINT}/v1/chat/completions",
            json=payload,
            timeout=self.settings.AI_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Local LLM API error: {response.status_code} - {response.text}")
        
        response_data = response.json()
        
        # Extract response content
        content = response_data['choices'][0]['message']['content']
        usage = response_data.get('usage', {})
        
        return {
            'response': content,
            'model': model,
            'provider': 'local',
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0),
            'confidence': 0.9  # Local models generally consistent
        }
    
    def _build_categorization_prompt(self, content: str) -> str:
        """Build prompt for CR categorization"""
        
        return f"""Analyze this change request and respond ONLY with valid JSON:

{content[:1500]}

Required JSON format:
{{
    "category": "emergency|standard|normal|enhancement|infrastructure|security|maintenance|rollback",
    "priority": "low|medium|high|critical", 
    "title": "concise title",
    "description": "brief summary",
    "affected_systems": ["system1", "system2"],
    "confidence": 0.85,
    "reasoning": "why this categorization"
}}

Respond with JSON only, no additional text."""
    
    def _build_risk_assessment_prompt(self, content: str) -> str:
        """Build prompt for risk assessment"""
        
        return f"""Risk assess this change request, respond with JSON only:

{content[:1200]}

Required JSON:
{{
    "risk_level": "low|medium|high",
    "risk_score": 1-9,
    "impact_score": 1-3,
    "probability_score": 1-3,
    "risk_factors": [{{"type": "technical", "description": "risk", "severity": "low|medium|high"}}],
    "mitigation_recommendations": ["recommendation"],
    "confidence": 0.8,
    "requires_additional_review": true
}}

JSON only, no extra text."""
    
    def _build_quality_check_prompt(self, content: str) -> str:
        """Build prompt for quality assessment"""
        
        return f"""Quality check this change request, respond with JSON only:

{content[:1000]}

Required JSON:
{{
    "quality_score": 0-100,
    "quality_issues": [{{"type": "missing_info", "severity": "low|medium|high", "description": "issue", "recommendation": "fix"}}],
    "completeness_check": {{"business_justification": "complete|incomplete", "technical_details": "complete|incomplete", "rollback_plan": "complete|incomplete"}},
    "compliance_flags": ["flag"],
    "confidence": 0.9,
    "overall_assessment": "brief summary"
}}

JSON only."""
    
    def _parse_categorization_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate categorization response"""
        
        try:
            # Extract JSON from response (handle markdown code blocks)
            response_text = result.get('response', '').strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Find JSON boundaries
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_data = json.loads(response_text[json_start:json_end])
                
                # Validate and normalize
                return {
                    'category': self._normalize_category(json_data.get('category', 'normal')),
                    'priority': self._normalize_priority(json_data.get('priority', 'medium')),
                    'title': json_data.get('title', 'Untitled Change Request')[:200],
                    'description': json_data.get('description', '')[:1000],
                    'affected_systems': json_data.get('affected_systems', [])[:10],  # Limit array size
                    'confidence': min(max(float(json_data.get('confidence', 0.5)), 0.0), 1.0),
                    'reasoning': json_data.get('reasoning', ''),
                    'provider': result.get('provider'),
                    'model': result.get('model'),
                    'tokens_used': result.get('total_tokens', 0)
                }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to parse categorization response", error=str(e))
        
        # Fallback parsing
        return self._rule_based_categorization(result.get('response', ''))
    
    def _parse_risk_assessment_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate risk assessment response"""
        
        try:
            # Extract JSON from response (handle markdown code blocks)
            response_text = result.get('response', '').strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Find JSON boundaries
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_data = json.loads(response_text[json_start:json_end])
                
                return {
                    'risk_level': self._normalize_risk_level(json_data.get('risk_level', 'medium')),
                    'risk_score': max(1, min(9, int(json_data.get('risk_score', 4)))),
                    'impact_score': max(1, min(3, int(json_data.get('impact_score', 2)))),
                    'probability_score': max(1, min(3, int(json_data.get('probability_score', 2)))),
                    'risk_factors': json_data.get('risk_factors', [])[:20],
                    'mitigation_recommendations': json_data.get('mitigation_recommendations', [])[:10],
                    'confidence': min(max(float(json_data.get('confidence', 0.5)), 0.0), 1.0),
                    'requires_additional_review': bool(json_data.get('requires_additional_review', False)),
                    'provider': result.get('provider'),
                    'model': result.get('model'),
                    'tokens_used': result.get('total_tokens', 0)
                }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to parse risk assessment response", error=str(e))
        
        return self._rule_based_risk_assessment(result.get('response', ''))
    
    def _parse_quality_check_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate quality check response"""
        
        try:
            # Extract JSON from response (handle markdown code blocks)
            response_text = result.get('response', '').strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Find JSON boundaries
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_data = json.loads(response_text[json_start:json_end])
                
                return {
                    'quality_score': max(0, min(100, int(json_data.get('quality_score', 50)))),
                    'quality_issues': json_data.get('quality_issues', [])[:50],
                    'completeness_check': json_data.get('completeness_check', {}),
                    'compliance_flags': json_data.get('compliance_flags', [])[:20],
                    'confidence': min(max(float(json_data.get('confidence', 0.5)), 0.0), 1.0),
                    'overall_assessment': json_data.get('overall_assessment', ''),
                    'provider': result.get('provider'),
                    'model': result.get('model'),
                    'tokens_used': result.get('total_tokens', 0)
                }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to parse quality check response", error=str(e))
        
        return self._rule_based_quality_check(result.get('response', ''))
    
    def _normalize_category(self, category: str) -> str:
        """Normalize category to valid enum value"""
        category_lower = category.lower().strip()
        
        valid_categories = [e.value for e in ChangeRequestCategory]
        
        if category_lower in valid_categories:
            return category_lower
        
        # Fuzzy matching
        if any(word in category_lower for word in ['emergency', 'urgent', 'critical']):
            return ChangeRequestCategory.EMERGENCY.value
        elif any(word in category_lower for word in ['standard', 'routine']):
            return ChangeRequestCategory.STANDARD.value
        elif any(word in category_lower for word in ['enhancement', 'feature', 'improvement']):
            return ChangeRequestCategory.ENHANCEMENT.value
        elif any(word in category_lower for word in ['infrastructure', 'hardware', 'network']):
            return ChangeRequestCategory.INFRASTRUCTURE.value
        elif any(word in category_lower for word in ['security', 'patch', 'vulnerability']):
            return ChangeRequestCategory.SECURITY.value
        elif any(word in category_lower for word in ['maintenance', 'update', 'upgrade']):
            return ChangeRequestCategory.MAINTENANCE.value
        elif any(word in category_lower for word in ['rollback', 'revert', 'back']):
            return ChangeRequestCategory.ROLLBACK.value
        
        return ChangeRequestCategory.NORMAL.value
    
    def _normalize_priority(self, priority: str) -> str:
        """Normalize priority to valid enum value"""
        priority_lower = priority.lower().strip()
        
        valid_priorities = [e.value for e in ChangeRequestPriority]
        
        if priority_lower in valid_priorities:
            return priority_lower
        
        # Fuzzy matching
        if any(word in priority_lower for word in ['critical', 'urgent', 'emergency']):
            return ChangeRequestPriority.CRITICAL.value
        elif any(word in priority_lower for word in ['high', 'important']):
            return ChangeRequestPriority.HIGH.value
        elif any(word in priority_lower for word in ['low', 'minor']):
            return ChangeRequestPriority.LOW.value
        
        return ChangeRequestPriority.MEDIUM.value
    
    def _normalize_risk_level(self, risk_level: str) -> str:
        """Normalize risk level to valid enum value"""
        risk_lower = risk_level.lower().strip()
        
        valid_risks = [e.value for e in ChangeRequestRisk]
        
        if risk_lower in valid_risks:
            return risk_lower
        
        return ChangeRequestRisk.MEDIUM.value
    
    def _rule_based_categorization(self, content: str) -> Dict[str, Any]:
        """Fallback rule-based categorization"""
        content_lower = content.lower()
        
        # Simple keyword-based categorization
        if any(word in content_lower for word in ['emergency', 'critical', 'outage', 'down']):
            category = ChangeRequestCategory.EMERGENCY.value
            priority = ChangeRequestPriority.CRITICAL.value
        elif any(word in content_lower for word in ['security', 'patch', 'vulnerability']):
            category = ChangeRequestCategory.SECURITY.value
            priority = ChangeRequestPriority.HIGH.value
        elif any(word in content_lower for word in ['enhancement', 'feature', 'improvement']):
            category = ChangeRequestCategory.ENHANCEMENT.value
            priority = ChangeRequestPriority.MEDIUM.value
        else:
            category = ChangeRequestCategory.NORMAL.value
            priority = ChangeRequestPriority.MEDIUM.value
        
        return {
            'category': category,
            'priority': priority,
            'title': content[:100] + '...' if len(content) > 100 else content,
            'description': content[:500] + '...' if len(content) > 500 else content,
            'affected_systems': [],
            'confidence': 0.3,  # Low confidence for rule-based
            'reasoning': 'Automatic rule-based categorization (AI services unavailable)',
            'provider': 'fallback',
            'model': 'rule-based',
            'tokens_used': 0
        }
    
    def _rule_based_risk_assessment(self, content: str) -> Dict[str, Any]:
        """Fallback rule-based risk assessment"""
        content_lower = content.lower()
        
        # Simple risk assessment based on keywords
        high_risk_keywords = ['production', 'database', 'critical', 'customer', 'revenue']
        medium_risk_keywords = ['system', 'application', 'service', 'integration']
        
        high_risk_count = sum(1 for keyword in high_risk_keywords if keyword in content_lower)
        medium_risk_count = sum(1 for keyword in medium_risk_keywords if keyword in content_lower)
        
        if high_risk_count >= 2:
            risk_level = ChangeRequestRisk.HIGH.value
            risk_score = 6
        elif high_risk_count >= 1 or medium_risk_count >= 3:
            risk_level = ChangeRequestRisk.MEDIUM.value
            risk_score = 4
        else:
            risk_level = ChangeRequestRisk.LOW.value
            risk_score = 2
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'impact_score': 2,
            'probability_score': 2,
            'risk_factors': [
                {'type': 'general', 'description': 'Rule-based assessment', 'severity': 'medium'}
            ],
            'mitigation_recommendations': ['Please perform manual risk assessment'],
            'confidence': 0.3,
            'requires_additional_review': True,
            'provider': 'fallback',
            'model': 'rule-based',
            'tokens_used': 0
        }
    
    def _rule_based_quality_check(self, content: str) -> Dict[str, Any]:
        """Fallback rule-based quality check"""
        
        # Simple quality scoring based on content length and keywords
        quality_score = 50  # Base score
        issues = []
        
        if len(content) < 100:
            quality_score -= 20
            issues.append({
                'type': 'insufficient_detail',
                'severity': 'high',
                'description': 'Document appears too brief',
                'location': 'overall',
                'recommendation': 'Provide more detailed information'
            })
        
        required_sections = ['business', 'technical', 'risk', 'testing', 'rollback']
        missing_sections = []
        
        for section in required_sections:
            if section not in content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            quality_score -= len(missing_sections) * 5
            issues.append({
                'type': 'missing_requirements',
                'severity': 'medium',
                'description': f'Missing sections: {", ".join(missing_sections)}',
                'location': 'document structure',
                'recommendation': 'Add missing sections'
            })
        
        return {
            'quality_score': max(0, min(100, quality_score)),
            'quality_issues': issues,
            'completeness_check': {
                'business_justification': 'incomplete',
                'technical_details': 'incomplete', 
                'implementation_plan': 'incomplete',
                'rollback_plan': 'incomplete',
                'testing_plan': 'incomplete'
            },
            'compliance_flags': ['Manual review required'],
            'confidence': 0.3,
            'overall_assessment': 'Basic rule-based quality assessment completed',
            'provider': 'fallback',
            'model': 'rule-based',
            'tokens_used': 0
        }
    
    async def _fallback_analysis(self, cr_id: str, content: str) -> Dict[str, Any]:
        """Complete fallback analysis when all AI services fail"""
        
        logger.warning("Using complete fallback analysis", cr_id=cr_id)
        
        categorization = self._rule_based_categorization(content)
        risk_assessment = self._rule_based_risk_assessment(content)
        quality_check = self._rule_based_quality_check(content)
        
        return {
            'categorization': categorization,
            'risk_assessment': risk_assessment,
            'quality_check': quality_check,
            'overall_confidence': 0.3,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'providers_used': ['fallback'],
            'fallback_used': True
        }
    
    def _calculate_overall_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence from individual analysis results"""
        confidences = []
        
        for result in results:
            if isinstance(result, dict) and 'confidence' in result:
                confidences.append(result['confidence'])
        
        if not confidences:
            return 0.5
        
        # Use average confidence, weighted towards lower values for conservatism
        avg_confidence = sum(confidences) / len(confidences)
        return round(avg_confidence * 0.9, 2)  # Apply 10% conservative adjustment
    
    def _get_providers_used(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract list of providers used in analysis"""
        providers = set()
        
        for result in results:
            if isinstance(result, dict) and 'provider' in result:
                providers.add(result['provider'])
        
        return list(providers)