# docs/resume_intelligence.md — Resume Intelligence Engine Documentation

This document describes the design, architecture, data schemas, caching,
and algorithms of the Resume Intelligence Engine (Phase 3).

---

## Architecture

The Resume Intelligence Engine is the "brain" of the AI Job Tracker. It translates
a semi-structured document (PDF, DOCX, or TXT) into a highly structured
Candidate Profile JSON.

Every downstream pipeline component (scrapers, filter, sheets) reads from this profile,
ensuring the resume is parsed exactly once and cached.

```
                  +-----------------------+
                  |  Newest Resume File   | (PDF/DOCX/TXT)
                  +-----------+-----------+
                              |
                              ▼
                  +-----------------------+
                  |    ResumeDetector     | (Locate newest file by mtime)
                  +-----------+-----------+
                              |
                              ▼
                  +-----------------------+
                  |    CacheManager       | (Compare SHA-256 file hashes)
                  +-----+-----------+-----+
                        |           |
             [Hash Match]           [Hash Mismatch]
                        |           |
                        ▼           ▼
             +------------+       +-------------------+
             | Load Cache |       |  ResumeExtractor  | (pdfplumber/docx text)
             +------------+       +---------+---------+
                                            |
                                            ▼
                                  +-------------------+
                                  |   SectionParser   | (regex & heuristic chunking)
                                  +---------+---------+
                                            |
                                            ▼
                                  +-------------------+
                                  |   SkillExpander   | (expand ~150 technologies)
                                  +---------+---------+
                                            |
                                            ▼
                                  +-------------------+
                                  |  InferenceEngine  | (score matching roles)
                                  +---------+---------+
                                            |
                                            ▼
                                  +-------------------+
                                  | KeywordGenerator  | (build 10 keyword groups)
                                  +---------+---------+
                                            |
                                            ▼
                                  +-------------------+
                                  |  QueryGenerator   | (Role x Location x Modifier)
                                  +---------+---------+
                                            |
                                            ▼
                                  +-------------------+
                                  | CandidateScorer   | (readiness, ATS, strengths)
                                  +---------+---------+
                                            |
                                            ▼
                                  +-------------------+
                                  |  ChangeDetector   | (generate diff report)
                                  +---------+---------+
                                            |
                                            ▼
                                  +-------------------+
                                  |   Save to Cache   | (JSON Profile & new hash)
                                  +-------------------+
```

---

## Design Decisions

### 1. Deterministic Offline Analysis
We deliberately avoided LLM API dependencies for this phase. Doing so makes this module:
- **Instantaneous**: complete execution in under 1 second.
- **Free**: zero token cost.
- **Durable**: works offline, doesn't break due to API deprecations or internet failures.
- **Reproducible**: identical input resumes guarantee identical outputs.

### 2. Hash-based Cache Verification
We SHA-256 fingerprint the resume file contents. If a user uploads a resume,
we read the cached hash. If they match, we return the cached CandidateProfile immediately,
bypassing PDF/DOCX file I/O which can take several hundred milliseconds.

### 3. Pydantic Master Model
Downstream tasks need to work with structured keys (e.g. `profile.skills.frameworks`).
A Pydantic model (`CandidateProfile`) enforces validation during both builder creation
and cache loading, converting messy strings into typed datasets.

---

## Caching Strategy

The cache operates on two files stored inside the `cache/` directory (gitignored):

1. **`cache/resume_hash.txt`**: stores the SHA-256 hex digest of the file bytes.
2. **`cache/candidate_profile.json`**: stores the serialized JSON model representation.

On pipeline invocation:
1. Scan for the newest file in `resume/`.
2. Compute the current SHA-256 hash.
3. Compare against `cache/resume_hash.txt`.
4. If identical, load `candidate_profile.json` and validate via Pydantic. If validation passes, return profile.
5. If hashes differ or validation fails, run full extraction, diff against the old profile to write a `change_report`, and save new files to cache.

---

## Skill Expansion Engine

The `SkillExpander` maps technical keywords to synonyms and broader domain terms using a curated static dictionary (`SKILL_EXPANSION_MAP` in `resume_parser/skill_expander.py`).

Example expansions:
- `FastAPI` $\rightarrow$ `["FastAPI", "Python Backend", "REST APIs", "Microservices", "API Development"]`
- `LangChain` $\rightarrow$ `["LangChain", "LLMs", "Prompt Engineering", "RAG", "Agentic AI", "Vector Databases"]`

This prevents search filters from missing jobs that request generic roles (e.g., "Python Developer") when the candidate lists specific frameworks.

---

## Role Inference & Scoring Engine

We match candidate skills against a list of standardized industry role profiles. Each profile contains:
- `required_skills`: Core skills critical to the role.
- `optional_skills`: Supplementary skills that boost eligibility.

### Score Formulas

$$\text{Base Score (70\% Weight)} = \left(\frac{\text{Matched Required Skills}}{\text{Total Required Skills}}\right) \times 70$$

$$\text{Boost Score (30\% Weight)} = \left(\frac{\text{Matched Optional Skills}}{\text{Total Optional Skills}}\right) \times 30$$

$$\text{Final Score} = \min(\text{Base Score} + \text{Boost Score}, 100)$$

If the final score is $\ge 50$, the role is included in the candidate profile's `inferred_roles` list.

---

## Testing Plan

We verify the engine using automated test suites in `tests/`:

1. **Unit tests (no filesystem dependancy)**:
   - Verify `profile_model` serialization.
   - Verify `skill_expander` output mapping.
   - Verify `inference_engine` score calculations.
   - Verify `keyword_generator` and `query_generator` query lengths.
   - Verify `scorer` readiness math.
2. **Integration tests**:
   - Provide plain text resume mock fixtures in `data/resumes/`.
   - Run `detector`, `extractor`, `section_parser`, and the overall `profile_builder` pipeline.

Run all tests using:
```bash
pytest tests/ -v
```

---

## Future Integration

In Phase 4, the job scraper will:
1. Load `cache/candidate_profile.json`.
2. Retrieve the search query combinations (`profile.search_queries`).
3. Feed these queries into search endpoints on LinkedIn, Indeed, and Google.

In Phase 5, the job filter will:
1. Load the job descriptions.
2. Intersect the job description keywords with `profile.keyword_groups.expanded_technical`.
3. Score relevance to customize matches for the candidate.
