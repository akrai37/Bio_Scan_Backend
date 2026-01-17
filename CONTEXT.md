# BioScan Backend - Context & Decisions

## Project Overview

**Name:** BioScan - AI Lab Assistant for Protocol Validation

**Purpose:** Analyze experimental protocols and flag potential issues before researchers waste time and money on failed experiments.

**Target Users:** Research scientists, lab managers, grad students

**Hackathon:** Disrupt Bio Hackathon (Jan 18, 2026, 12pm-6pm)

## The Problem We're Solving

- 30% of research experiments fail due to preventable protocol errors
- Failed experiments waste $50B+ annually
- Common issues: missing controls, unsafe conditions, vague methods

## What BioScan Does

1. User uploads experimental protocol (PDF)
2. AI extracts text and analyzes for:
   - **Critical Issues (Red 🔴):** Missing controls, safety risks, contamination
   - **Warnings (Yellow 🟡):** Unclear sample sizes, vague concentrations
   - **Passed Checks (Green 🟢):** Good practices, proper controls
3. Returns:
   - Success probability (0-100%)
   - Estimated cost & time
   - Actionable suggestions for improvement

## Key Design Decisions

### Why Multiple LLM Support?
- **Groq (default):** Free tier, no credit card needed, fast inference
- **Claude:** Best quality for structured extraction (when budget allows)
- **OpenAI:** Widely available, good balance

Strategy: Start free (Groq), upgrade later if needed.

### Why FastAPI?
- Modern, fast Python framework
- Auto-generated API docs (`/docs`)
- Easy async support
- Type hints built-in

### Why PDF-only?
- Most protocols are PDFs
- Keeps scope manageable for 6-hour hackathon
- Text extraction is a solved problem

### File Size Limit (20MB)
- Prevents abuse
- Most protocols are < 5MB
- Avoids timeouts

## Technical Constraints

- **Time:** 6 hours on Sunday (most building done Friday night)
- **Budget:** Free tier only (Groq)
- **Demo:** Must work flawlessly in 2-minute presentation
- **Deployment:** None required for hackathon (local only)

## Success Criteria

### For Judging:
- ✅ Works reliably in live demo
- ✅ Catches real protocol issues
- ✅ Clear value proposition (saves time/money)
- ✅ Professional UI

### For Investment:
- Shows clear market opportunity ($50B problem)
- Defensible moat (network effects from protocol data)
- Scalable architecture

## What Makes This Winnable

1. **Demo Impact:** Upload flawed protocol → AI catches it in 10 seconds → "Holy shit" moment
2. **Clear ROI:** "We saved this lab $12K by catching a missing control"
3. **Low Technical Risk:** Just LLM + PDF parsing (no complex integrations)
4. **Real Problem:** Every researcher has wasted time on failed experiments

## Future Enhancements (Post-Hackathon)

- Protocol library (learn from past analyses)
- Cost prediction from supplier APIs
- Multi-file support (protocols + papers)
- Real-time collaboration
- Mobile app

## Current State (Friday Night Build)

- [x] Backend structure complete
- [x] Multi-LLM support (Groq/Claude/OpenAI)
- [x] PDF parsing
- [x] Analysis endpoint
- [ ] Frontend (next)
- [ ] Testing with real protocols
- [ ] Demo prep

---

**Last Updated:** January 16, 2026 - Initial build
**Next Steps:** Build frontend, test with sample protocols
