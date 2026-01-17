import os
from abc import ABC, abstractmethod
from typing import Dict, List
import json
import re

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def analyze_protocol(self, protocol_text: str) -> Dict:
        """Analyze protocol and return structured results"""
        pass
    
    def _parse_analysis(self, raw_response: str) -> Dict:
        """Parse LLM response into structured format"""
        try:
            # Try to extract JSON if wrapped in markdown
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try direct JSON parse
            return json.loads(raw_response)
        except json.JSONDecodeError:
            # Fallback: basic parsing
            return {
                "success_probability": 50,
                "critical_issues": [{"issue": "Unable to parse detailed analysis", "description": "Please try again"}],
                "warnings": [],
                "passed_checks": [],
                "suggestions": ["Please try uploading the protocol again"],
                "raw_analysis": raw_response
            }


class GroqProvider(LLMProvider):
    """Groq LLM Provider (Free tier available)"""
    
    def __init__(self):
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-70b-versatile"  # Fast and capable
    
    def analyze_protocol(self, protocol_text: str) -> Dict:
        """Analyze protocol using Groq"""
        
        prompt = self._build_analysis_prompt(protocol_text)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert scientific protocol reviewer with deep knowledge of experimental design, safety protocols, and common experimental pitfalls. Analyze protocols critically but constructively."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            parsed = self._parse_analysis(result)
            parsed["raw_analysis"] = result
            return parsed
            
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")
    
    def _build_analysis_prompt(self, protocol_text: str) -> str:
        """Build the analysis prompt"""
        return f"""Analyze the following experimental protocol for potential issues and success probability.

PROTOCOL TEXT:
{protocol_text[:8000]}  

Evaluate the protocol on these criteria:

**CRITICAL ISSUES** (Red flags - likely to cause failure):
- Missing negative control
- Missing positive control
- No replication stated
- Unsafe temperatures or conditions
- Contamination risks
- Incompatible reagents
- Vague or missing concentrations for key reagents

**WARNINGS** (Yellow flags - should improve):
- Unclear sample size
- Vague incubation times
- Missing buffer compositions
- No mention of controls (but could be implied)
- Statistical analysis not specified

**GOOD PRACTICES** (Green checks):
- Appropriate controls present
- Clear replication (n= specified)
- Safety protocols mentioned
- Detailed methodology
- Proper concentrations stated

Based on your analysis, estimate:
1. Success probability (0-100%)
2. Rough cost estimate if possible
3. Time estimate if possible
4. Concrete suggestions for improvement

Return your analysis as a JSON object with this exact structure:
{{
    "success_probability": <integer 0-100>,
    "critical_issues": [
        {{"issue": "<short title>", "description": "<detailed explanation>"}}
    ],
    "warnings": [
        {{"issue": "<short title>", "description": "<detailed explanation>"}}
    ],
    "passed_checks": [
        {{"check": "<what passed>", "description": "<why it's good>"}}
    ],
    "estimated_cost": "<rough USD estimate or 'Unknown'>",
    "estimated_time": "<rough time estimate or 'Unknown'>",
    "suggestions": ["<concrete actionable suggestion>"]
}}

Be specific and reference actual details from the protocol. If information is missing, flag it."""


class ClaudeProvider(LLMProvider):
    """Anthropic Claude Provider"""
    
    def __init__(self):
        from anthropic import Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def analyze_protocol(self, protocol_text: str) -> Dict:
        """Analyze protocol using Claude"""
        
        prompt = self._build_analysis_prompt(protocol_text)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            result = response.content[0].text
            parsed = self._parse_analysis(result)
            parsed["raw_analysis"] = result
            return parsed
            
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")
    
    def _build_analysis_prompt(self, protocol_text: str) -> str:
        """Build the analysis prompt (same as Groq for consistency)"""
        return GroqProvider._build_analysis_prompt(self, protocol_text)


class OpenAIProvider(LLMProvider):
    """OpenAI GPT Provider"""
    
    def __init__(self):
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Cost effective
    
    def analyze_protocol(self, protocol_text: str) -> Dict:
        """Analyze protocol using OpenAI"""
        
        prompt = self._build_analysis_prompt(protocol_text)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert scientific protocol reviewer. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            parsed = self._parse_analysis(result)
            parsed["raw_analysis"] = result
            return parsed
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _build_analysis_prompt(self, protocol_text: str) -> str:
        """Build the analysis prompt (same as Groq for consistency)"""
        return GroqProvider._build_analysis_prompt(self, protocol_text)


def get_llm_provider() -> LLMProvider:
    """Factory function to get the configured LLM provider"""
    provider_name = os.getenv("LLM_PROVIDER", "groq").lower()
    
    providers = {
        "groq": GroqProvider,
        "claude": ClaudeProvider,
        "openai": OpenAIProvider
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown LLM provider: {provider_name}. Available: {list(providers.keys())}")
    
    return providers[provider_name]()
