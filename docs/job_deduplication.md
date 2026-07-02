# docs/job_deduplication.md — Intelligent Deduplication & Cross-Platform Validation

This document describes the design, standardizations, text similarity checks, and
master selection priority rules of the Job Deduplication Engine (Phase 8).

---

## Deduplication Architecture

The deduplication module acts as a cross-platform resolver, validating listings,
standardizing data fields, calculating text similarities, and merging duplicates.

```
[Scored Listings] (cache/matched_jobs.json)
         │
         ▼
   JobDeduplicator
         │
         ├─► 1. URL Normalizer (standardizes hostnames, strips UTM trackers)
         ├─► 2. Entity Normalizer (Company aliases, Role Title synonyms, Location mapping)
         ├─► 3. Text Similarity (fast Jaccard word overlaps + SequenceMatcher description ratio)
         └─► 4. Data Validator (validates rules, calculates Validation/Trust scores)
         │
         ▼
   Master Job Selection (Source priority sorting, merges alternate_sources links)
         │
         ▼
[Deduplicated Masters & References] (cache/deduplicated_jobs.json)
```

---

## Multi-Level Standardizations

### 1. Canonical URL Standardizer
Strips UTM parameters, referral tags, and tracker flags. Canonicalizes LinkedIn view links
to standard structures:
- Input: `https://www.linkedin.com/jobs/view/12345?refId=abc&trackingId=xyz`
- Output: `https://www.linkedin.com/jobs/view/12345`

### 2. Company Alias Normalization
Standardizes variations of parent companies, strips legal suffixes, and maps common local subsidiaries:
- `Google LLC`, `Google India Pvt Ltd` $\rightarrow$ `Google`
- `NVIDIA Corp`, `Nvidia Corporation` $\rightarrow$ `Nvidia`

### 3. Role Title Normalizer
Groups related titles using semantic synonyms:
- `Applied AI Engineer`, `LLM Engineer`, `Generative AI Engineer` $\rightarrow$ `AI Engineer`
- `Python AI Developer`, `AI Backend Developer` $\rightarrow$ `AI Backend Engineer`

### 4. Location Normalizer
Standardizes cities and remote categories:
- `Hyderabad, India`, `Hyderabad, Telangana` $\rightarrow$ `Hyderabad`
- `Work From Home`, `Remote India`, `wfh` $\rightarrow$ `Remote`

---

## High-Performance Similarity Strategy

Comparing multi-thousand character description texts can slow down throughput. To prevent scaling bottlenecks, we use a two-tiered comparison strategy:

1. **Jaccard Token Similarity** (Fast O(N)): Compares word set overlaps. If the Jaccard coefficient is below 25%, the job is immediately flagged as unique, skipping expensive string calculations.
2. **difflib.SequenceMatcher** (Precise O(N*M)): Compares sequential character ratio of the first 200 words. Used to confirm duplicates if the Jaccard coefficient passes the check.

---

## Master Job Selection Priority

When duplicate job listings are identified across multiple sources, a single **Master Job** is created using the priority ranking configured in `config/dedup_rules.json`:

1. Company Careers Pages
2. Google / Microsoft / Amazon / NVIDIA Careers
3. LinkedIn
4. Wellfound
5. Naukri / Indeed / Instahyre
6. Other sources

All alternative application links are appended to `alternate_sources: list[dict[str, str]]` under the master listing, preserving alternative links if the primary source expires.
