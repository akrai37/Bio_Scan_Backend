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
    
    @abstractmethod
    def generate_fix(self, issue: str, description: str, protocol_context: str) -> Dict:
        """Generate a specific fix for an identified issue"""
        pass
    
    @abstractmethod
    def generate_improved_protocol(self, original_protocol: str, fixes_to_apply: List[Dict]) -> Dict:
        """Generate an improved version of the protocol with fixes applied"""
        pass
    
    @abstractmethod
    def extract_reagents(self, protocol_text: str) -> Dict:
        """Extract ALL reagents from protocol and generate shopping list with pricing"""
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
        self.model = "llama-3.3-70b-versatile"  # Updated model
    
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

    def generate_fix(self, issue: str, description: str, protocol_context: str) -> Dict:
        """Generate a specific fix for an identified issue using Groq"""
        
        prompt = f"""You are an expert protocol designer. A specific issue has been identified in an experimental protocol.

ISSUE: {issue}
DESCRIPTION: {description}

PROTOCOL CONTEXT:
{protocol_context[:4000]}

Generate a concrete, actionable fix for this issue. Provide:
1. A clear fix suggestion (2-3 sentences explaining what to add/change)
2. Step-by-step implementation instructions

Return your response as a JSON object with this exact structure:
{{
    "fix_suggestion": "<clear explanation of the fix>",
    "implementation_steps": [
        "<step 1>",
        "<step 2>",
        "<step 3>"
    ]
}}

Be specific and actionable. Reference actual protocol details when possible."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert protocol designer who provides clear, actionable solutions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            parsed = json.loads(result)
            return parsed
            
        except Exception as e:
            raise Exception(f"Groq API error generating fix: {str(e)}")

    def generate_improved_protocol(self, original_protocol: str, fixes_to_apply: List[Dict]) -> Dict:
        """Generate an improved version of the protocol with fixes applied"""
        
        fixes_summary = "\n\n".join([
            f"ISSUE: {fix['issue']}\n" +
            f"DESCRIPTION: {fix.get('description', '')}\n" +
            f"FIX: {fix['fix_suggestion']}\n" +
            f"IMPLEMENTATION:\n" + "\n".join([f"  {i+1}. {step}" for i, step in enumerate(fix.get('implementation_steps', []))])
            for fix in fixes_to_apply
        ])
        
        prompt = f"""You are an expert protocol editor. You need to make TARGETED, SURGICAL changes to this protocol - ONLY for the specific issues listed below.

ORIGINAL PROTOCOL:
{original_protocol[:6000]}

SELECTED FIXES TO APPLY:
{fixes_summary}

CRITICAL INSTRUCTIONS:
1. Start with the EXACT original protocol text
2. Make ONLY the specific changes needed for the fixes listed above
3. DO NOT rewrite or improve other parts of the protocol
4. Keep everything else EXACTLY as it was in the original
5. DO NOT make changes to parts of the protocol not mentioned in the fixes

Your output should be the original protocol with MINIMAL, TARGETED modifications for only the selected issues.

Also estimate the new success probability (0-100%) for the improved protocol based on the fixes applied.

Return your response as a JSON object with this exact structure:
{{
    "improved_protocol": "<the protocol with ONLY the selected fixes applied>",
    "changes_made": [
- Each mention should include specifications (concentration, quantity, etc.)
- This ensures shopping list will match what's needed

Your output should be the original protocol with MINIMAL, TARGETED modifications for only the selected issues, plus a complete Materials section update.

Also estimate the new success probability (0-100%) for the improved protocol based on the fixes applied.

Return your response as a JSON object with this exact structure:
{{
    "improved_protocol": "<the protocol with ONLY the selected fixes applied AND complete Materials section>",
    "changes_made": [
        "<specific change 1 - what was added/modified>",
        "<specific change 2 - what was added/modified>"
    ],
    "new_success_probability": <integer 0-100>
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert protocol editor who makes precise, targeted improvements."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            parsed = json.loads(result)
            return parsed
            
        except Exception as e:
            raise Exception(f"Groq API error generating improved protocol: {str(e)}")

    def extract_reagents(self, protocol_text: str) -> Dict:
        """Extract ALL reagents from protocol and generate shopping list with pricing"""
        
        prompt = f"""You are a text extraction specialist. Extract ONLY materials that are EXPLICITLY written word-for-word in the Materials section below.

PROTOCOL TEXT:
{protocol_text[:4000]}

**🚨 ANTI-HALLUCINATION RULES - STRICTLY ENFORCE:**

DO NOT add materials from your own knowledge.
DO NOT infer materials that "should" be there.
DO NOT be helpful by suggesting additional items.
DO NOT use your training knowledge of typical lab protocols.

If a material is NOT written word-for-word in the Materials section above, DO NOT include it.

**STEP 1: LOCATE THE MATERIALS SECTION**
Find the section labeled "Materials" in the protocol text above.
Read ONLY that section. Ignore all other sections.

**STEP 2: QUOTE VERIFICATION (MANDATORY)**
For EACH item you want to extract, you MUST be able to point to the exact phrase in the Materials section.
If you cannot find the exact text, DO NOT include it.

**STEP 3: EXTRACT ONLY WHAT'S THERE**
Copy the item names EXACTLY as written.
DO NOT expand, DO NOT add related items, DO NOT be creative.

**EXAMPLES OF HALLUCINATION (FORBIDDEN):**
❌ Materials says "buffer" → You add "wash buffer" (WRONG - you invented "wash")
❌ Materials says "antibody" → You add "blocking buffer" (WRONG - not mentioned)
❌ Materials lists 5 items → You return 8 items (WRONG - you added 3)
❌ You add "tubes" or "pipette tips" (WRONG - unless explicitly written)

**CORRECT BEHAVIOR:**
✅ Materials says "Primary antibody (1:1000)" → Extract: "Primary antibody (1:1000)"
✅ Materials says "buffer" → Extract: "buffer" (NOT "wash buffer" or "blocking buffer")
✅ Materials has 5 items → Return EXACTLY 5 items

**FINAL VERIFICATION BEFORE RETURNING:**
Go through your list and verify EACH item appears verbatim in the Materials section text above.
Remove ANY item you cannot directly quote from the original Materials section.
Count: If Materials has N items, your output MUST have exactly N items.

PROTOCOL:
{protocol_text[:4000]}

**🚨 CRITICAL DEMO REQUIREMENT - READ CAREFULLY:**

This shopping list will be shown side-by-side with the protocol in a hackathon demo.
The judges MUST see a PERFECT 1-to-1 match between the Materials section and the shopping list.
If you add items not in Materials = looks like AI hallucination (DEMO FAILS)
If you skip items in Materials = looks like broken feature (DEMO FAILS)

**YOUR EXACT TASK:**
1. Find the "Materials" section in the protocol above
2. Extract EVERY item listed in that Materials section
3. Extract NOTHING else - no assumptions, no helpful additions
4. Use EXACT names as written (copy-paste accuracy)

**FORBIDDEN BEHAVIORS (These will cause demo failure):**
✗ DO NOT extract from "Procedure" / "Protocol Steps" / "Methods" sections
✗ DO NOT extract from "Notes" / "Quality Control" sections
✗ DO NOT add "common lab items" (pipette tips, tubes, gloves, timer, ice)
✗ DO NOT expand abbreviations (if Materials says "BSA", don't say "Bovine Serum Albumin")
✗ DO NOT add related items (if Materials says "buffer", don't add "wash buffer")
✗ DO NOT assume typical ELISA/PCR/Western blot reagents
✗ DO NOT be helpful - this is TEXT EXTRACTION, not protocol design

**REQUIRED BEHAVIOR:**
✓ Materials lists "Anti-IL-6 antibody" → Shopping list shows "Anti-IL-6 antibody"
✓ Materials lists "PBS (pH 7.4)" → Shopping list shows "PBS (pH 7.4)"
✓ Materials lists "96-well plate" → Shopping list shows "96-well plate"
✓ Materials has 5 items → Shopping list shows EXACTLY 5 items
✓ Materials has 12 items → Shopping list shows EXACTLY 12 items

**LITMUS TEST:**
Before returning, ask yourself: "Can I draw a line from each shopping list item to its exact match in the Materials section?"
If NO → You invented something → DELETE IT
If YES → Perfect match → Include it

**CONCRETE EXAMPLE - STUDY THIS:**
If the Materials section contains:
"Primary antibody (1:1000), secondary antibody (1:5000), buffer, detection reagent, and assay plate."

Then your JSON should have EXACTLY 5 items total:
1. Primary antibody (1:1000)
2. Secondary antibody (1:5000)  
3. Buffer
4. Detection reagent
5. Assay plate

DO NOT ADD:
✗ "tubes" - NOT in Materials
✗ "wash buffer" - Materials says "buffer", not "wash buffer"
✗ "pipette tips" - NOT in Materials
✗ "PBS" - NOT in Materials
✗ "blocking buffer" - NOT in Materials

If it's not explicitly written in Materials, DELETE IT from your output.

For PRICING ONLY:
- Use reasonable market prices: Antibodies $150-400, Enzymes $80-250, Buffers $30-90

Return JSON:
{{
    "categories": [
        {{
            "name": "Antibodies & Proteins",
            "items": [
                {{
                    "name": "<exact name from protocol>",
                    "concentration": "<exact value from protocol or empty>",
                    "quantity": "<exact value from protocol or empty>",
                    "estimated_price": <price>,
                    "checked": false
                }}
            ]
        }},
        {{
            "name": "Reagents & Substrates",
            "items": [...]
        }},
        {{
            "name": "Consumables",
            "items": [...]
        }},
        {{
            "name": "Buffers & Solutions",
            "items": [...]
        }}
    ],
    "total_cost": 0
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a laboratory procurement specialist who extracts reagent lists from protocols."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            parsed = json.loads(result)
            
            # Calculate total cost
            total = sum(
                item["estimated_price"]
                for category in parsed.get("categories", [])
                for item in category.get("items", [])
            )
            parsed["total_cost"] = total
            
            return parsed
            
        except Exception as e:
            raise Exception(f"Groq API error extracting reagents: {str(e)}")


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

    def generate_fix(self, issue: str, description: str, protocol_context: str) -> Dict:
        """Generate a specific fix using Claude"""
        prompt = f"""You are an expert protocol designer. A specific issue has been identified in an experimental protocol.

ISSUE: {issue}
DESCRIPTION: {description}

PROTOCOL CONTEXT:
{protocol_context[:4000]}

Generate a concrete, actionable fix for this issue. Provide:
1. A clear fix suggestion (2-3 sentences explaining what to add/change)
2. Step-by-step implementation instructions

Return your response as a JSON object with this exact structure:
{{
    "fix_suggestion": "<clear explanation of the fix>",
    "implementation_steps": [
        "<step 1>",
        "<step 2>",
        "<step 3>"
    ]
}}

Be specific and actionable. Reference actual protocol details when possible."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.4,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            result = response.content[0].text
            parsed = json.loads(result)
            return parsed
            
        except Exception as e:
            raise Exception(f"Claude API error generating fix: {str(e)}")

    def generate_improved_protocol(self, original_protocol: str, fixes_to_apply: List[Dict]) -> Dict:
        """Generate improved protocol using Claude"""
        fixes_summary = "\n\n".join([
            f"ISSUE: {fix['issue']}\n" +
            f"DESCRIPTION: {fix.get('description', '')}\n" +
            f"FIX: {fix['fix_suggestion']}\n" +
            f"IMPLEMENTATION:\n" + "\n".join([f"  {i+1}. {step}" for i, step in enumerate(fix.get('implementation_steps', []))])
            for fix in fixes_to_apply
        ])
        
        prompt = f"""You are an expert protocol editor. Apply the following fixes to the protocol.

ORIGINAL PROTOCOL:
{original_protocol[:6000]}

FIXES TO APPLY:
{fixes_summary}

INSTRUCTIONS:
1. Copy the original protocol text
2. For each fix listed above, find the relevant section and make the specific change
3. Add missing information where specified (temperatures, concentrations, controls, etc.)
4. If a fix introduces NEW materials/reagents/controls/information, apply it EVERYWHERE it's relevant:
   - Add to Materials section at the top
   - Add to the specific protocol step where it's used
   - Add to any other sections that reference it
5. Ensure consistency throughout - if you add something, it should be mentioned in all relevant places
6. If a fix requires adding a new section (e.g., control group), add it in the appropriate place
7. Keep other parts of the protocol unchanged
8. The improved protocol MUST be different from the original - the fixes MUST be visible

CONSISTENCY RULE:
- Any material/reagent/control added by a fix must be referenced consistently throughout the protocol
- Materials section must list everything mentioned anywhere in the protocol
- Each mention should be complete with specifications (concentration, quantity, timing, etc.)
- This ensures the protocol is internally consistent and the shopping list will be accurate

IMPORTANT: The "improved_protocol" field MUST show actual changes. Don't just copy the original.
For example:
- If a fix says "add temperature", the protocol must show "incubate at 37°C" instead of just "incubate"
- If a fix says "add negative control", the protocol must have a new control group section
- If a fix says "specify concentration", the protocol must show "2 mg/ml" instead of just "antibody"
- If a fix adds BSA for blocking, BSA must be in BOTH the Materials section AND the blocking step

Estimate the new success probability based on:
- Original score + (5-10% per critical issue fixed) + (2-3% per warning fixed)
- Don't go above 85-90% unless ALL major issues are fixed

Return your response as a JSON object:
{{
    "improved_protocol": "<the complete protocol with fixes applied - MUST be different from original>",
    "changes_made": [
        "<what was added/changed for fix 1>",
        "<what was added/changed for fix 2>"
    ],
    "new_success_probability": <integer 0-100>
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.5,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            result = response.content[0].text
            parsed = json.loads(result)
            return parsed
            
        except Exception as e:
            raise Exception(f"Claude API error generating improved protocol: {str(e)}")

    def extract_reagents(self, protocol_text: str) -> Dict:
        """Extract ALL reagents from protocol and generate shopping list with pricing"""
        
        prompt = f"""You are a text extraction specialist. Extract ONLY materials that are EXPLICITLY written word-for-word in the Materials section below.

PROTOCOL TEXT:
{protocol_text[:4000]}

**🚨 ANTI-HALLUCINATION RULES - STRICTLY ENFORCE:**

DO NOT add materials from your own knowledge.
DO NOT infer materials that "should" be there.
DO NOT be helpful by suggesting additional items.
DO NOT use your training knowledge of typical lab protocols.

If a material is NOT written word-for-word in the Materials section above, DO NOT include it.

**STEP 1: LOCATE THE MATERIALS SECTION**
Find the section labeled "Materials" in the protocol text above.
Read ONLY that section. Ignore all other sections.

**STEP 2: QUOTE VERIFICATION (MANDATORY)**
For EACH item you want to extract, you MUST be able to point to the exact phrase in the Materials section.
If you cannot find the exact text, DO NOT include it.

**STEP 3: EXTRACT ONLY WHAT'S THERE**
Copy the item names EXACTLY as written.
DO NOT expand, DO NOT add related items, DO NOT be creative.

**EXAMPLES OF HALLUCINATION (FORBIDDEN):**
❌ Materials says "buffer" → You add "wash buffer" (WRONG - you invented "wash")
❌ Materials says "antibody" → You add "blocking buffer" (WRONG - not mentioned)
❌ Materials lists 5 items → You return 8 items (WRONG - you added 3)
❌ You add "tubes" or "pipette tips" (WRONG - unless explicitly written)

**CORRECT BEHAVIOR:**
✅ Materials says "Primary antibody (1:1000)" → Extract: "Primary antibody (1:1000)"
✅ Materials says "buffer" → Extract: "buffer" (NOT "wash buffer" or "blocking buffer")
✅ Materials has 5 items → Return EXACTLY 5 items

**FINAL VERIFICATION BEFORE RETURNING:**
Go through your list and verify EACH item appears verbatim in the Materials section text above.
Remove ANY item you cannot directly quote from the original Materials section.
Count: If Materials has N items, your output MUST have exactly N items.

**YOUR EXACT TASK:**
1. Find the "Materials" section in the protocol above
2. Extract EVERY item listed in that Materials section
3. Extract NOTHING else - no assumptions, no helpful additions
4. Use EXACT names as written (copy-paste accuracy)

**FORBIDDEN BEHAVIORS (These will cause demo failure):**
✗ DO NOT extract from "Procedure" / "Protocol Steps" / "Methods" sections
✗ DO NOT extract from "Notes" / "Quality Control" sections
✗ DO NOT add "common lab items" (pipette tips, tubes, gloves, timer, ice)
✗ DO NOT expand abbreviations (if Materials says "BSA", don't say "Bovine Serum Albumin")
✗ DO NOT add related items (if Materials says "buffer", don't add "wash buffer")
✗ DO NOT assume typical ELISA/PCR/Western blot reagents
✗ DO NOT be helpful - this is TEXT EXTRACTION, not protocol design

**REQUIRED BEHAVIOR:**
✓ Materials lists "Anti-IL-6 antibody" → Shopping list shows "Anti-IL-6 antibody"
✓ Materials lists "PBS (pH 7.4)" → Shopping list shows "PBS (pH 7.4)"
✓ Materials lists "96-well plate" → Shopping list shows "96-well plate"
✓ Materials has 5 items → Shopping list shows EXACTLY 5 items
✓ Materials has 12 items → Shopping list shows EXACTLY 12 items

**LITMUS TEST:**
Before returning, ask yourself: "Can I draw a line from each shopping list item to its exact match in the Materials section?"
If NO → You invented something → DELETE IT
If YES → Perfect match → Include it

**CONCRETE EXAMPLE - STUDY THIS:**
If the Materials section contains:
"Primary antibody (1:1000), secondary antibody (1:5000), buffer, detection reagent, and assay plate."

Then your JSON should have EXACTLY 5 items total:
1. Primary antibody (1:1000)
2. Secondary antibody (1:5000)  
3. Buffer
4. Detection reagent
5. Assay plate

DO NOT ADD:
✗ "tubes" - NOT in Materials
✗ "wash buffer" - Materials says "buffer", not "wash buffer"
✗ "pipette tips" - NOT in Materials
✗ "PBS" - NOT in Materials
✗ "blocking buffer" - NOT in Materials

If it's not explicitly written in Materials, DELETE IT from your output.

For PRICING ONLY:
- Use reasonable market prices: Antibodies $150-400, Enzymes $80-250, Buffers $30-90

Return JSON:
{{
    "categories": [
        {{
            "name": "Antibodies & Proteins",
            "items": [{{"name": "...", "concentration": "...", "quantity": "...", "estimated_price": 0, "checked": false}}]
        }},
        {{"name": "Reagents & Substrates", "items": [...]}},
        {{"name": "Consumables", "items": [...]}},
        {{"name": "Buffers & Solutions", "items": [...]}}
    ],
    "total_cost": 0
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                temperature=0.4,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            result = response.content[0].text
            parsed = json.loads(result)
            
            # Calculate total cost
            total = sum(
                item["estimated_price"]
                for category in parsed.get("categories", [])
                for item in category.get("items", [])
            )
            parsed["total_cost"] = total
            
            return parsed
            
        except Exception as e:
            raise Exception(f"Claude API error extracting reagents: {str(e)}")


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

    def generate_fix(self, issue: str, description: str, protocol_context: str) -> Dict:
        """Generate a specific fix using OpenAI"""
        prompt = f"""You are an expert protocol designer. A specific issue has been identified in an experimental protocol.

ISSUE: {issue}
DESCRIPTION: {description}

PROTOCOL CONTEXT:
{protocol_context[:4000]}

Generate a concrete, actionable fix for this issue. Provide:
1. A clear fix suggestion (2-3 sentences explaining what to add/change)
2. Step-by-step implementation instructions

Return your response as a JSON object with this exact structure:
{{
    "fix_suggestion": "<clear explanation of the fix>",
    "implementation_steps": [
        "<step 1>",
        "<step 2>",
        "<step 3>"
    ]
}}

Be specific and actionable. Reference actual protocol details when possible."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert protocol designer who provides clear, actionable solutions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            parsed = json.loads(result)
            return parsed
            
        except Exception as e:
            raise Exception(f"OpenAI API error generating fix: {str(e)}")

    def generate_improved_protocol(self, original_protocol: str, fixes_to_apply: List[Dict]) -> Dict:
        """Generate improved protocol using OpenAI"""
        fixes_summary = "\n\n".join([
            f"ISSUE: {fix['issue']}\n" +
            f"DESCRIPTION: {fix.get('description', '')}\n" +
            f"FIX: {fix['fix_suggestion']}\n" +
            f"IMPLEMENTATION:\n" + "\n".join([f"  {i+1}. {step}" for i, step in enumerate(fix.get('implementation_steps', []))])
            for fix in fixes_to_apply
        ])
        
        prompt = f"""You are an expert protocol editor. Apply the following fixes to the protocol.

ORIGINAL PROTOCOL:
{original_protocol[:6000]}

FIXES TO APPLY:
{fixes_summary}

INSTRUCTIONS:
1. Copy the original protocol text
2. For each fix listed above, find the relevant section and make the specific change
3. Add missing information where specified (temperatures, concentrations, controls, etc.)
4. If a fix introduces NEW materials/reagents/controls/information, apply it EVERYWHERE it's relevant:
   - Add to Materials section at the top
   - Add to the specific protocol step where it's used
   - Add to any other sections that reference it
5. Ensure consistency throughout - if you add something, it should be mentioned in all relevant places
6. If a fix requires adding a new section (e.g., control group), add it in the appropriate place
7. Keep other parts of the protocol unchanged
8. The improved protocol MUST be different from the original - the fixes MUST be visible

CONSISTENCY RULE:
- Any material/reagent/control added by a fix must be referenced consistently throughout the protocol
- Materials section must list everything mentioned anywhere in the protocol
- Each mention should be complete with specifications (concentration, quantity, timing, etc.)
- This ensures the protocol is internally consistent and the shopping list will be accurate

IMPORTANT: The "improved_protocol" field MUST show actual changes. Don't just copy the original.
For example:
- If a fix says "add temperature", the protocol must show "incubate at 37°C" instead of just "incubate"
- If a fix says "add negative control", the protocol must have a new control group section
- If a fix says "specify concentration", the protocol must show "2 mg/ml" instead of just "antibody"
- If a fix adds BSA for blocking, BSA must be in BOTH the Materials section AND the blocking step AND anywhere else it's referenced

Estimate the new success probability based on:
- Original score + (5-10% per critical issue fixed) + (2-3% per warning fixed)
- Don't go above 85-90% unless ALL major issues are fixed

Return your response as a JSON object:
{{
    "improved_protocol": "<the complete protocol with fixes applied - MUST be different from original>",
    "changes_made": [
        "<what was added/changed for fix 1>",
        "<what was added/changed for fix 2>"
    ],
    "new_success_probability": <integer 0-100>
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert protocol editor who makes precise, targeted improvements."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            parsed = json.loads(result)
            return parsed
            
        except Exception as e:
            raise Exception(f"OpenAI API error generating improved protocol: {str(e)}")

    def extract_reagents(self, protocol_text: str) -> Dict:
        """Extract ALL reagents from protocol and generate shopping list with pricing"""
        
        prompt = f"""You are a text extraction specialist. Extract ONLY materials that are EXPLICITLY written word-for-word in the Materials section below.

PROTOCOL TEXT:
{protocol_text[:4000]}

**🚨 ANTI-HALLUCINATION RULES - STRICTLY ENFORCE:**

DO NOT add materials from your own knowledge.
DO NOT infer materials that "should" be there.
DO NOT be helpful by suggesting additional items.
DO NOT use your training knowledge of typical lab protocols.

If a material is NOT written word-for-word in the Materials section above, DO NOT include it.

**STEP 1: LOCATE THE MATERIALS SECTION**
Find the section labeled "Materials" in the protocol text above.
Read ONLY that section. Ignore all other sections.

**STEP 2: QUOTE VERIFICATION (MANDATORY)**
For EACH item you want to extract, you MUST be able to point to the exact phrase in the Materials section.
If you cannot find the exact text, DO NOT include it.

**STEP 3: EXTRACT ONLY WHAT'S THERE**
Copy the item names EXACTLY as written.
DO NOT expand, DO NOT add related items, DO NOT be creative.

**EXAMPLES OF HALLUCINATION (FORBIDDEN):**
❌ Materials says "buffer" → You add "wash buffer" (WRONG - you invented "wash")
❌ Materials says "antibody" → You add "blocking buffer" (WRONG - not mentioned)
❌ Materials lists 5 items → You return 8 items (WRONG - you added 3)
❌ You add "tubes" or "pipette tips" (WRONG - unless explicitly written)

**CORRECT BEHAVIOR:**
✅ Materials says "Primary antibody (1:1000)" → Extract: "Primary antibody (1:1000)"
✅ Materials says "buffer" → Extract: "buffer" (NOT "wash buffer" or "blocking buffer")
✅ Materials has 5 items → Return EXACTLY 5 items

**FINAL VERIFICATION BEFORE RETURNING:**
Go through your list and verify EACH item appears verbatim in the Materials section text above.
Remove ANY item you cannot directly quote from the original Materials section.
Count: If Materials has N items, your output MUST have exactly N items.

**🚨 CRITICAL DEMO REQUIREMENT - READ CAREFULLY:**

This shopping list will be shown side-by-side with the protocol in a hackathon demo.
The judges MUST see a PERFECT 1-to-1 match between the Materials section and the shopping list.
If you add items not in Materials = looks like AI hallucination (DEMO FAILS)
If you skip items in Materials = looks like broken feature (DEMO FAILS)

**YOUR EXACT TASK:**
1. Find the "Materials" section in the protocol above
2. Extract EVERY item listed in that Materials section
3. Extract NOTHING else - no assumptions, no helpful additions
4. Use EXACT names as written (copy-paste accuracy)

**FORBIDDEN BEHAVIORS (These will cause demo failure):**
✗ DO NOT extract from "Procedure" / "Protocol Steps" / "Methods" sections
✗ DO NOT extract from "Notes" / "Quality Control" sections
✗ DO NOT add "common lab items" (pipette tips, tubes, gloves, timer, ice)
✗ DO NOT expand abbreviations (if Materials says "BSA", don't say "Bovine Serum Albumin")
✗ DO NOT add related items (if Materials says "buffer", don't add "wash buffer")
✗ DO NOT assume typical ELISA/PCR/Western blot reagents
✗ DO NOT be helpful - this is TEXT EXTRACTION, not protocol design

**REQUIRED BEHAVIOR:**
✓ Materials lists "Anti-IL-6 antibody" → Shopping list shows "Anti-IL-6 antibody"
✓ Materials lists "PBS (pH 7.4)" → Shopping list shows "PBS (pH 7.4)"
✓ Materials lists "96-well plate" → Shopping list shows "96-well plate"
✓ Materials has 5 items → Shopping list shows EXACTLY 5 items
✓ Materials has 12 items → Shopping list shows EXACTLY 12 items

**LITMUS TEST:**
Before returning, ask yourself: "Can I draw a line from each shopping list item to its exact match in the Materials section?"
If NO → You invented something → DELETE IT
If YES → Perfect match → Include it

**CONCRETE EXAMPLE - STUDY THIS:**
If the Materials section contains:
"Primary antibody (1:1000), secondary antibody (1:5000), buffer, detection reagent, and assay plate."

Then your JSON should have EXACTLY 5 items total:
1. Primary antibody (1:1000)
2. Secondary antibody (1:5000)  
3. Buffer
4. Detection reagent
5. Assay plate

DO NOT ADD:
✗ "tubes" - NOT in Materials
✗ "wash buffer" - Materials says "buffer", not "wash buffer"
✗ "pipette tips" - NOT in Materials
✗ "PBS" - NOT in Materials
✗ "blocking buffer" - NOT in Materials

If it's not explicitly written in Materials, DELETE IT from your output.

For PRICING ONLY:
- Use reasonable market prices: Antibodies $150-400, Enzymes $80-250, Buffers $30-90

Return JSON:
{{
    "categories": [
        {{
            "name": "Antibodies & Proteins",
            "items": [{{"name": "...", "concentration": "...", "quantity": "...", "estimated_price": 0, "checked": false}}]
        }},
        {{"name": "Reagents & Substrates", "items": [...]}},
        {{"name": "Consumables", "items": [...]}},
        {{"name": "Buffers & Solutions", "items": [...]}}
    ],
    "total_cost": 0
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a laboratory procurement specialist who extracts reagent lists from protocols."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            parsed = json.loads(result)
            
            # Calculate total cost
            total = sum(
                item["estimated_price"]
                for category in parsed.get("categories", [])
                for item in category.get("items", [])
            )
            parsed["total_cost"] = total
            
            return parsed
            
        except Exception as e:
            raise Exception(f"OpenAI API error extracting reagents: {str(e)}")


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
