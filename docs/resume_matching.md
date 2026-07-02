# docs/resume_matching.md — Resume Matching & Candidate Scoring Engine

This document describes the design, scoring formulas, and explanation generation
components of the Intelligent Resume Matching Engine (Phase 7).

---

## Matching Architecture

The resume matching layer behaves like a virtual technical recruiter, scoring each
opportunity across three logically independent dimensions before combining them into a
weighted overall score.

```
[Filtered Listings] (cache/filtered_jobs.json)
         │
         ▼
   ResumeMatcher
         │
         ├─► 1. Eligibility Score (Location, Exp limit, Batch 2027)
         ├─► 2. Technical Match Score (Skills matching, Projects, Internships, Certs)
         └─► 3. Career Fit Score (Role category, vertical domains, goals)
         │
         ▼
   SemanticIntelligence (Synonym & Tech mapping lookups)
         │
         ▼
   MatchExplainer (Compiles strengths, weaknesses, resume tailoring improvements)
         │
         ▼
[Aggregated Match Score & Explanations] (cache/matched_jobs.json)
```

---

## Scoring Formulas

The overall Match Score is determined by the weighted contribution of three sub-scores:

$$\text{Match Score} = 0.20 \times \text{Eligibility} + 0.50 \times \text{Technical} + 0.30 \times \text{Career Fit}$$

### 1. Eligibility Score (20% Weight)
Ensures basic logistical compatibility:
- **Location Fit** (30% weight): Remote (100%), preferred cities (100%), other India cities (70%).
- **Experience Match** (30% weight): Discarded (0%) if required years $> 1$.
- **Graduation eligibility** (40% weight): Asserts batch 2027 is eligible (100%).

### 2. Technical Score (50% Weight)
Evaluates tech stack and capability fit:
- **Skills Match** (40% weight): Proportion of candidate's technical skills matching job requirements.
- **Projects Match** (30% weight): Evaluates matching project tech stacks.
- **Internship Match** (20% weight): Checks matching duration and role keywords.
- **Certifications** (10% weight): Validates matching certificates.

### 3. Career Fit Score (30% Weight)
Reviews career goals alignment:
- **Role Match** (40% weight): Compares preferred titles (Applied AI, GenAI).
- **Domain Match** (30% weight): Reviews company vertical domains (SaaS, FinTech).
- **Goal Match** (30% weight): Matches long-term career priorities.

---

## Match Category Thresholds

Scored opportunities are classified into categories to simplify scheduling decisions:

- **Excellent Match** ($\ge 85\%$): Automated notification trigger candidate. High compatibility.
- **Strong Match** ($70\% - 84\%$): Highly recommended for immediate application.
- **Good Match** ($55\% - 69\%$): Valid target, fits profile well.
- **Potential Match** ($40\% - 54\%$): Needs minor skill mapping.
- **Needs Skill Improvement** ($25\% - 39\%$): Missing several tech stacks.
- **Reject** ($< 25\%$): Unrelated or incompatible.

---

## Explainable AI Design

Every evaluation compiles a feedback report containing:
- **Strengths**: Matches on target roles, locations, or strong technical scores.
- **Weaknesses**: Missing preferred tools, mismatching domains.
- **Suggestions for Tailoring**: Dynamic advice suggesting which project to emphasize or which internship experience to highlight.
- **Skills to learn**: Prioritized list of missing keywords.
- **Confidence Rating**: Scans description content length and reliability ratings.
- **Risk Score**: Evaluates risk parameters based on mismatching elements.
