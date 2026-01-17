# BioScan Backend - LLM Prompts

This file contains all prompts used for LLM analysis. Keep this updated when prompts are modified.

---

## System Prompt (Used by all providers)

**Role:** Set LLM's behavior and expertise

```
You are an expert scientific protocol reviewer with deep knowledge of experimental design, safety protocols, and common experimental pitfalls. Analyze protocols critically but constructively.
```

**Why this works:**
- Establishes expertise
- Encourages critical but helpful analysis
- Sets professional tone

---

## Main Analysis Prompt

**Location:** `llm_providers.py` → `_build_analysis_prompt()`

**Template:**

```
Analyze the following experimental protocol for potential issues and success probability.

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
{
    "success_probability": <integer 0-100>,
    "critical_issues": [
        {"issue": "<short title>", "description": "<detailed explanation>"}
    ],
    "warnings": [
        {"issue": "<short title>", "description": "<detailed explanation>"}
    ],
    "passed_checks": [
        {"check": "<what passed>", "description": "<why it's good>"}
    ],
    "estimated_cost": "<rough USD estimate or 'Unknown'>",
    "estimated_time": "<rough time estimate or 'Unknown'>",
    "suggestions": ["<concrete actionable suggestion>"]
}

Be specific and reference actual details from the protocol. If information is missing, flag it.
```

---

## Prompt Design Principles

### 1. Structured Evaluation
- Clear categories (Critical/Warning/Good)
- Specific examples of what to look for
- Prevents vague analysis

### 2. Actionable Output
- JSON format forces structure
- Short title + detailed description
- Enables UI parsing

### 3. Specificity
- "Be specific and reference actual details"
- Prevents generic responses
- Makes analysis credible

### 4. Cost/Time Estimation
- Optional ("if possible")
- Adds value when LLM can infer
- Shows comprehensive thinking

---

## Critical Issues Checklist

The prompt explicitly looks for:

| Issue | Why Critical | Example |
|-------|--------------|---------|
| Missing negative control | Can't prove specificity | No enzyme control in enzyme assay |
| Missing positive control | Can't validate system works | No known activator control |
| No replication | Can't assess reliability | Single experiment, no n= |
| Unsafe temps | Protein denaturation, fire | 95°C for heat-sensitive enzyme |
| Contamination risk | False results | No sterile technique mentioned |
| Incompatible reagents | Chemical reaction failure | Mixing EDTA with calcium-dependent enzyme |
| Vague concentrations | Non-reproducible | "Add some salt" |

---

## Warnings Checklist

| Warning | Why Important | Example |
|---------|---------------|---------|
| Unclear sample size | Hard to assess power | "Multiple samples" instead of n=5 |
| Vague times | Non-reproducible | "Incubate briefly" |
| Missing buffers | pH affects results | "In solution" (which solution?) |
| No statistical plan | Can't validate claims | No mention of t-test, ANOVA |

---

## Good Practices Checklist

| Practice | Why Good | Example |
|----------|----------|---------|
| Controls present | Validates specificity | Positive + negative controls |
| Clear replication | Statistical validity | "n=5 biological replicates" |
| Safety mentioned | Shows awareness | "Work in fume hood" |
| Detailed methods | Reproducible | Exact concentrations, times |

---

## Response Format Requirements

### JSON Schema Expected

```json
{
  "success_probability": 0-100,
  "critical_issues": [
    {
      "issue": "Missing negative control",
      "description": "Protocol does not include a no-enzyme control to validate specificity of the reaction."
    }
  ],
  "warnings": [
    {
      "issue": "Unclear sample size",
      "description": "Protocol states 'multiple replicates' without specifying n=."
    }
  ],
  "passed_checks": [
    {
      "check": "Positive control present",
      "description": "Protocol includes known activator as positive control."
    }
  ],
  "estimated_cost": "$5,000-$8,000",
  "estimated_time": "4-6 weeks",
  "suggestions": [
    "Add negative control (no enzyme)",
    "Specify n=5 biological replicates",
    "Include buffer composition (pH, salt concentration)"
  ]
}
```

### Fallback Parsing

If JSON parsing fails:
1. Try extracting JSON from markdown code blocks
2. If still fails, return generic error with raw response
3. User can see LLM output for debugging

---

## Temperature Setting

```python
temperature=0.3  # Lower = more consistent
```

**Why 0.3?**
- Consistent analysis across runs
- Less creative hallucination
- More factual, less speculative
- Good for structured tasks

---

## Token Limits

### Input
- Protocol text truncated to **8000 chars**
- Prevents token limit errors
- Most protocols fit comfortably

### Output
- Max tokens: **2000**
- Enough for detailed analysis
- Prevents runaway generation

---

## Provider-Specific Settings

### Groq
```python
model="llama-3.1-70b-versatile"
temperature=0.3
max_tokens=2000
response_format={"type": "json_object"}
```

### Claude
```python
model="claude-3-5-sonnet-20241022"
temperature=0.3
max_tokens=2000
# No native JSON mode, parse from output
```

### OpenAI
```python
model="gpt-4o-mini"
temperature=0.3
max_tokens=2000
response_format={"type": "json_object"}
```

---

## Future Prompt Improvements

### Phase 2 (Post-Hackathon)
- Add cost estimation database (reagent prices)
- Include safety warnings (OSHA guidelines)
- Reference similar protocols (success/failure rates)
- Species-specific considerations (mouse vs human cells)

### Phase 3 (Advanced)
- Multi-turn conversation (ask clarifying questions)
- Protocol optimization suggestions
- Alternative method recommendations
- Literature references for best practices

---

## Example Outputs

### High-Quality Protocol (Score: 85%)

```json
{
  "success_probability": 85,
  "critical_issues": [],
  "warnings": [
    {
      "issue": "Statistical test not specified",
      "description": "While n=5 is stated, no mention of which statistical test will be used for comparison."
    }
  ],
  "passed_checks": [
    {
      "check": "All controls present",
      "description": "Both positive (TNF-α) and negative (media only) controls included."
    },
    {
      "check": "Clear replication",
      "description": "n=5 biological replicates clearly stated."
    },
    {
      "check": "Detailed methodology",
      "description": "All reagent concentrations, incubation times, and buffer compositions specified."
    }
  ],
  "estimated_cost": "$3,000-$4,000",
  "estimated_time": "3 weeks",
  "suggestions": [
    "Specify statistical test (e.g., one-way ANOVA with Tukey post-hoc)",
    "Consider adding a time-course to optimize incubation time"
  ]
}
```

### Problematic Protocol (Score: 35%)

```json
{
  "success_probability": 35,
  "critical_issues": [
    {
      "issue": "Missing negative control",
      "description": "No untreated or vehicle control included. Cannot determine if observed effects are specific."
    },
    {
      "issue": "Unsafe temperature",
      "description": "Protocol specifies 65°C incubation for protein with known denaturation at 50°C."
    },
    {
      "issue": "Vague reagent concentration",
      "description": "States 'add antibody' without specifying concentration or volume."
    }
  ],
  "warnings": [
    {
      "issue": "No replication stated",
      "description": "Protocol does not mention number of replicates or independent experiments."
    },
    {
      "issue": "Missing buffer details",
      "description": "States 'in PBS' but does not specify pH or if supplements are included."
    }
  ],
  "passed_checks": [
    {
      "check": "Positive control mentioned",
      "description": "Includes known ligand as positive control."
    }
  ],
  "estimated_cost": "Unknown (insufficient detail)",
  "estimated_time": "Unknown (likely multiple iterations needed)",
  "suggestions": [
    "Add negative control (untreated cells or vehicle)",
    "Reduce incubation temperature to 37°C based on protein stability data",
    "Specify antibody concentration (e.g., 1:1000 dilution)",
    "State n=3 minimum biological replicates",
    "Include PBS formulation (pH 7.4, with or without Ca2+/Mg2+)"
  ]
}
```

---

**Last Updated:** January 16, 2026 - Initial prompt design
**Version:** 1.0
