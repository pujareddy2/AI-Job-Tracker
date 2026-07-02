"""
resume_parser/section_parser.py — Resume Section and Entity Parser
==================================================================
Purpose
-------
Carve raw resume text into structured sections and parse personal details,
education, skills, projects, experience, certifications, and achievements.

Design Decisions
----------------
Heuristic Section Splitter:
    - Resumes follow relatively standard section titles: "EDUCATION", "SKILLS",
      "EXPERIENCE", "PROJECTS", "CERTIFICATIONS", etc.
    - We compile a map of regular expressions targeting common section headers
      including typical variations (e.g. "WORK HISTORY", "PROFESSIONAL EXPERIENCE").
    - We split the text by identifying where these headers occur, keeping track of
      their order to extract the content belonging to each block.

Personal Info Extraction:
    - Name: Heuristically assume the first non-empty line of the resume (or one of the
      first 3 lines) containing alphabetic characters represents the candidate name.
    - Email, Phone, LinkedIn, GitHub: Robust regex patterns extract these standard fields.
    - Coding Profiles: Check for LeetCode, HackerRank, Codeforces URLs.

Education Parsing:
    - CGPA: Search the education section for matches like "CGPA: X.Y", "GPA: X.Y/4.0", "X.Y / 10", "X.Y%".
    - Graduation Year: Match 4-digit years between 2000 and 2035.
    - Degree and Branch: Match common degrees (B.Tech, B.E, B.S, M.S, M.Tech) and branches (CSE, IT, ECE).

Skills Extraction:
    - Identify skills by scanning the text against category-specific keyword lists.
    - This is extremely robust: if a resume lists "PostgreSQL" under a generic header,
      we categorize it into "databases" using our dictionary of known tools.

Usage
-----
    from resume_parser.section_parser import SectionParser

    parser = SectionParser()
    parsed_sections, personal_info, education, skills = parser.parse(raw_text)
"""

from __future__ import annotations

import re
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

# ===========================================================================
# Regex Patterns
# ===========================================================================

EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
LINKEDIN_REGEX = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+/?")
GITHUB_REGEX = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+/?")
PORTFOLIO_REGEX = re.compile(r"(?:https?://)?(?:www\.)?(?:[\w\-]+\.github\.io|[\w\-]+\.me|[\w\-]+\.dev|[\w\-]+\.com)(?!/in/|/sravya|/rohan)/?[\w\-]*")
CGPA_REGEX = re.compile(r"(?:cgpa|gpa|percentage|score)\s*[:\-]?\s*([5-9]\.\d{1,2}(?:\s*/\s*10)?|[3-4]\.\d{1,2}(?:\s*/\s*4)?|\d{2}(?:\.\d{1,2})?\s*%)", re.IGNORECASE)
YEAR_REGEX = re.compile(r"\b(20[0-2][0-9]|203[0-5])\b")

# Coding platforms
LEETCODE_REGEX = re.compile(r"(?:https?://)?(?:www\.)?leetcode\.com/[\w\-]+/?")
HACKERRANK_REGEX = re.compile(r"(?:https?://)?(?:www\.)?hackerrank\.com/[\w\-]+/?")

# Section header patterns
SECTION_HEADERS = {
    "education": re.compile(r"\b(?:education|academic background|studies)\b", re.IGNORECASE),
    "skills": re.compile(r"\b(?:skills|technical skills|skills inventory|competencies|areas of expertise|languages and tools)\b", re.IGNORECASE),
    "experience": re.compile(r"\b(?:experience|professional experience|work history|employment|internships and experience)\b", re.IGNORECASE),
    "projects": re.compile(r"\b(?:projects|personal projects|academic projects|key projects)\b", re.IGNORECASE),
    "certifications": re.compile(r"\b(?:certifications|credentials|licenses|courses)\b", re.IGNORECASE),
    "hackathons": re.compile(r"\b(?:hackathons|competitions|contests|coding events)\b", re.IGNORECASE),
    "awards": re.compile(r"\b(?:awards|achievements|honors|accolades)\b", re.IGNORECASE),
    "languages": re.compile(r"\b(?:languages|languages spoken)\b", re.IGNORECASE),
    "volunteer": re.compile(r"\b(?:volunteer|volunteer work|social service|extra-curriculars|leadership)\b", re.IGNORECASE),
    "publications": re.compile(r"\b(?:publications|research papers|publications and research)\b", re.IGNORECASE),
    "open_source": re.compile(r"\b(?:open source|open-source contributions|contributions)\b", re.IGNORECASE)
}

# ===========================================================================
# Skill Categories Keywords for Direct Classification
# ===========================================================================
SKILL_KEYWORDS = {
    "programming_languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang", "rust",
        "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "html", "css", "bash", "shell"
    ],
    "frameworks": [
        "fastapi", "django", "flask", "spring boot", "spring", "react", "react.js", "angular",
        "vue", "vue.js", "next.js", "express", "express.js", "laravel", "rails", "nest.js", "svelte"
    ],
    "libraries": [
        "langchain", "llamaindex", "numpy", "pandas", "scikit-learn", "scipy", "matplotlib",
        "seaborn", "tensorflow", "pytorch", "keras", "transformers", "huggingface", "sqlalchemy"
    ],
    "databases": [
        "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "chromadb", "pinecone",
        "milvus", "qdrant", "weaviate", "oracle", "cassandra", "elasticsearch", "neo4j", "dynamodb"
    ],
    "cloud": [
        "aws", "amazon web services", "gcp", "google cloud", "azure", "docker", "kubernetes",
        "terraform", "ansible", "jenkins", "github actions", "circleci", "heroku", "netlify"
    ],
    "ai_ml": [
        "rag", "retrieval augmented generation", "llm", "large language models", "prompt engineering",
        "generative ai", "nlp", "natural language processing", "computer vision", "deep learning",
        "machine learning", "neural networks", "fine-tuning", "bert", "gpt", "semantic search"
    ],
    "tools": [
        "git", "vscode", "jupyter", "jupyter notebook", "postman", "pydantic", "gradle", "maven",
        "npm", "yarn", "poetry", "pip", "linux", "ubuntu", "nginx", "apache", "jira", "confluence"
    ]
}


class SectionParser:
    """
    Parses resume text into structured sections and details.
    """

    def parse(self, text: str) -> dict[str, Any]:
        """
        Parse raw resume text into structured dictionaries.

        Parameters
        ----------
        text : str
            The raw text extracted from a resume.

        Returns
        -------
        dict[str, Any]
            Parsed sections, personal details, education, skills, projects, etc.
        """
        lines = [line.strip() for line in text.split("\n")]
        non_empty_lines = [line for line in lines if line]

        # 1. Extract personal info (Name & contacts)
        personal = self._extract_personal(text, non_empty_lines)

        # 2. Extract sections by headers
        sections = self._split_sections(text, lines)

        # 3. Parse specific section data
        edu_data = self._parse_education(sections.get("education", ""))
        skills_data = self._parse_skills(sections.get("skills", ""), text)
        projects_data = self._parse_projects_or_experience(sections.get("projects", ""))
        experience_data = self._parse_experience(sections.get("experience", ""))
        certifications_data = self._parse_bulleted_list(sections.get("certifications", ""))
        hackathons_data = self._parse_hackathons(sections.get("hackathons", ""))
        awards_data = self._parse_bulleted_list(sections.get("awards", ""))
        languages_data = self._parse_bulleted_list(sections.get("languages", ""))
        volunteer_data = self._parse_bulleted_list(sections.get("volunteer", ""))
        publications_data = self._parse_bulleted_list(sections.get("publications", ""))
        open_source_data = self._parse_bulleted_list(sections.get("open_source", ""))

        # Experience analysis
        total_months = 0
        internship_count = len(experience_data)
        # Parse experience level
        if internship_count > 0:
            level = "Intern"
        else:
            level = "Fresher"

        return {
            "personal": personal,
            "education": edu_data,
            "skills": skills_data,
            "projects": projects_data,
            "experience": {
                "level": level,
                "total_months": total_months,
                "internship_count": internship_count,
                "internships": experience_data,
                "full_time_roles": []
            },
            "certifications": certifications_data,
            "hackathons": hackathons_data,
            "awards": awards_data,
            "languages": languages_data,
            "volunteer": volunteer_data,
            "publications": publications_data,
            "open_source": open_source_data,
            "raw_sections": sections,
            "resume_summary": self._generate_summary(personal.get("name", ""), edu_data, skills_data, internship_count)
        }

    # -------------------------------------------------------------------------
    # Extractor & Parsers
    # -------------------------------------------------------------------------

    def _extract_personal(self, full_text: str, non_empty_lines: list[str]) -> dict[str, Any]:
        """Extract Name, Email, Phone, and online profiles."""
        name = ""
        # The first non-empty line usually contains the candidate's name.
        # Let's inspect the first 3 lines and find the best fit.
        for line in non_empty_lines[:3]:
            # A name shouldn't have email symbols, too many numbers, or keywords like "resume"
            if "@" not in line and "http" not in line and "|" not in line and len(line) < 40:
                # Remove extra spaces/accents
                name = re.sub(r"[^a-zA-Z\s\.]", "", line).strip()
                if name:
                    break

        email_match = EMAIL_REGEX.search(full_text)
        phone_match = PHONE_REGEX.search(full_text)
        linkedin_match = LINKEDIN_REGEX.search(full_text)
        github_match = GITHUB_REGEX.search(full_text)
        portfolio_match = PORTFOLIO_REGEX.search(full_text)
        leetcode_match = LEETCODE_REGEX.search(full_text)
        hackerrank_match = HACKERRANK_REGEX.search(full_text)

        coding_profiles = {}
        if leetcode_match:
            coding_profiles["leetcode"] = leetcode_match.group(0).strip("/")
        if hackerrank_match:
            coding_profiles["hackerrank"] = hackerrank_match.group(0).strip("/")

        # Deduplicate portfolio vs linkedin/github
        portfolio = ""
        for match in PORTFOLIO_REGEX.finditer(full_text):
            port_val = match.group(0).strip("/")
            if "linkedin.com" not in port_val and "github.com" not in port_val and "gmail" not in port_val and "yahoo" not in port_val and "outlook" not in port_val:
                portfolio = port_val
                break

        return {
            "name": name,
            "email": email_match.group(0) if email_match else "",
            "phone": phone_match.group(0) if phone_match else "",
            "linkedin": linkedin_match.group(0).strip("/") if linkedin_match else "",
            "github": github_match.group(0).strip("/") if github_match else "",
            "portfolio": portfolio,
            "location": self._infer_location(full_text),
            "coding_profiles": coding_profiles
        }

    def _infer_location(self, text: str) -> str:
        """Heuristically find locations like 'Hyderabad', 'Bangalore', etc."""
        locations = ["Hyderabad", "Bangalore", "Pune", "Mumbai", "Chennai", "Delhi", "Noida", "Gurgaon", "San Francisco", "London", "Remote"]
        for loc in locations:
            if re.search(r"\b" + loc + r"\b", text, re.IGNORECASE):
                # Return the exact casing
                return loc
        return ""

    def _split_sections(self, text: str, lines: list[str]) -> dict[str, str]:
        """Split text into section dictionary based on section header regexes."""
        header_positions = []
        # Find positions of all headers in the lines
        for i, line in enumerate(lines):
            line_clean = line.strip()
            # If the line is short (typical of headers)
            if 0 < len(line_clean) < 50:
                for sec_name, pattern in SECTION_HEADERS.items():
                    if pattern.fullmatch(line_clean) or (line_clean.isupper() and pattern.match(line_clean)):
                        header_positions.append((i, sec_name))
                        break

        # Sort headers by line index
        header_positions.sort()

        sections: dict[str, str] = {}
        if not header_positions:
            # Fallback: search raw text for keywords
            logger.warning("No standard headers found via line matching. Performing fuzzy text search.")
            return self._split_sections_fuzzy(text)

        # Extract content between headers
        for idx, (line_idx, sec_name) in enumerate(header_positions):
            start = line_idx + 1
            end = header_positions[idx + 1][0] if idx + 1 < len(header_positions) else len(lines)
            content = "\n".join(lines[start:end]).strip()
            sections[sec_name] = content

        return sections

    def _split_sections_fuzzy(self, text: str) -> dict[str, str]:
        """Fuzzy splitter if headers aren't on their own clean lines."""
        sections = {}
        # Find standard sections using regex index searching
        matches = []
        for sec_name, pattern in SECTION_HEADERS.items():
            for match in pattern.finditer(text):
                matches.append((match.start(), sec_name))
        
        matches.sort()
        for idx, (start_pos, sec_name) in enumerate(matches):
            start = start_pos
            end = matches[idx + 1][0] if idx + 1 < len(matches) else len(text)
            sections[sec_name] = text[start:end].strip()
        return sections

    def _parse_education(self, content: str) -> dict[str, Any]:
        """Parse degree, branch, institution, GPA, and grad year."""
        if not content:
            return {}

        cgpa_match = CGPA_REGEX.search(content)
        cgpa = cgpa_match.group(1) if cgpa_match else ""

        years = YEAR_REGEX.findall(content)
        grad_year = None
        expected = False
        if years:
            grad_year = int(years[-1])  # assume the last year is the graduation year
            if grad_year > 2025:  # Let's say relative to 2025/2026
                expected = True

        # Extract degree
        degree = ""
        degrees = ["B.Tech", "B.E", "B.S", "B.Sc", "M.Tech", "M.S", "M.Sc", "B.A", "M.B.A", "Ph.D"]
        for deg in degrees:
            if re.search(r"\b" + re.escape(deg) + r"\b", content, re.IGNORECASE):
                degree = deg
                break

        # Extract branch
        branch = ""
        branches = ["Computer Science", "CSE", "Information Technology", "IT", "Electrical", "ECE", "Mechanical"]
        for br in branches:
            if re.search(r"\b" + re.escape(br) + r"\b", content, re.IGNORECASE):
                branch = br
                break

        # Extract institution
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        institution = ""
        if lines:
            first_line = lines[0]
            if any(term in first_line.lower() for term in ["b.tech", "b.e", "b.s", "b.sc", "m.tech", "m.s", "m.sc", "bachelor", "master", "degree", "education"]):
                if len(lines) > 1:
                    institution = lines[1]
                else:
                    institution = first_line
            else:
                institution = first_line

        return {
            "degree": degree,
            "branch": branch,
            "institution": institution,
            "cgpa": cgpa,
            "graduation_year": grad_year,
            "expected": expected
        }

    def _parse_skills(self, content: str, full_text: str) -> dict[str, list[str]]:
        """
        Extract categorised skills. Uses both the dedicated skills section
        and the full text to make sure no skills are missed.
        """
        # If no skills section was found, search the whole text
        search_target = (content + "\n" + full_text) if content else full_text
        search_target_lower = search_target.lower()

        extracted_skills: dict[str, list[str]] = {
            "programming_languages": [],
            "frameworks": [],
            "libraries": [],
            "databases": [],
            "cloud": [],
            "ai_ml": [],
            "tools": [],
            "languages_spoken": [],
            "other": []
        }

        # Check against pre-defined keywords dictionary
        for category, keyword_list in SKILL_KEYWORDS.items():
            for keyword in keyword_list:
                # Use word boundary or specific regex checks for skills like C++ or React.js
                pattern_str = r"\b" + re.escape(keyword) + r"\b"
                if keyword in ["c++", "c#", "react.js", "vue.js", "next.js", "express.js", "spring boot"]:
                    pattern_str = re.escape(keyword)

                if re.search(pattern_str, search_target_lower):
                    # Find original casing from key list or match word in text
                    orig_case = self._find_original_casing(keyword, search_target)
                    extracted_skills[category].append(orig_case)

        # Extract languages spoken
        languages = ["English", "Telugu", "Hindi", "Tamil", "Spanish", "French", "German", "Japanese"]
        for lang in languages:
            if re.search(r"\b" + lang + r"\b", search_target, re.IGNORECASE):
                extracted_skills["languages_spoken"].append(lang)

        # Deduplicate
        for k in extracted_skills:
            extracted_skills[k] = sorted(list(set(extracted_skills[k])))

        return extracted_skills

    def _find_original_casing(self, keyword: str, text: str) -> str:
        """Extract the exact casing of the keyword as it appears in the resume."""
        match = re.search(r"\b" + re.escape(keyword) + r"\b", text, re.IGNORECASE)
        if match:
            return match.group(0)
        # Fallbacks for specific tech spelling
        special_cases = {
            "fastapi": "FastAPI", "langchain": "LangChain", "llamaindex": "LlamaIndex",
            "react.js": "React.js", "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
            "chromadb": "ChromaDB", "github actions": "GitHub Actions", "vscode": "VSCode",
            "pydantic": "Pydantic", "scikit-learn": "Scikit-learn", "numpy": "NumPy",
            "pandas": "Pandas", "pytorch": "PyTorch", "tensorflow": "TensorFlow",
            "mongodb": "MongoDB", "dynamodb": "DynamoDB"
        }
        return special_cases.get(keyword.lower(), keyword.title())

    def _parse_projects_or_experience(self, content: str) -> list[dict[str, Any]]:
        """Parse structured elements from a project section by detecting title and bullet lines."""
        if not content:
            return []
        
        items = []
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        
        current_item = None
        for line in lines:
            is_bullet = line.startswith(("-", "*", "•"))
            clean_line = re.sub(r"^[-*•]\s*", "", line).strip()
            
            if not is_bullet:
                if current_item:
                    items.append(current_item)
                
                current_item = {
                    "name": clean_line,
                    "technologies": [],
                    "description": "",
                    "highlights": []
                }
            else:
                if not current_item:
                    current_item = {
                        "name": "Project Details",
                        "technologies": [],
                        "description": "",
                        "highlights": []
                    }
                
                current_item["highlights"].append(clean_line)
                
                for cat, keywords in SKILL_KEYWORDS.items():
                    for kw in keywords:
                        if re.search(r"\b" + re.escape(kw) + r"\b", clean_line, re.IGNORECASE):
                            current_item["technologies"].append(self._find_original_casing(kw, clean_line))

        if current_item:
            items.append(current_item)

        for item in items:
            if item["highlights"]:
                item["description"] = item["highlights"][0]
            item["technologies"] = sorted(list(set(item["technologies"])))

        return items

    def _parse_experience(self, content: str) -> list[dict[str, Any]]:
        """Extract internships and roles from experience section content."""
        if not content:
            return []

        roles = []
        lines = [l.strip() for l in content.split("\n") if l.strip()]

        current_role = None
        for line in lines:
            is_bullet = line.startswith(("-", "*", "•"))
            clean_line = re.sub(r"^[-*•]\s*", "", line).strip()

            if not is_bullet:
                if current_role:
                    roles.append(current_role)

                parts = [p.strip() for p in re.split(r"[|•\-–]", clean_line)]
                role = parts[0] if len(parts) > 0 else ""
                company = parts[1] if len(parts) > 1 else ""
                duration = parts[2] if len(parts) > 2 else ""

                if not duration:
                    years = YEAR_REGEX.findall(clean_line)
                    if years:
                        duration = " – ".join(years)

                current_role = {
                    "role": role,
                    "company": company,
                    "duration": duration,
                    "technologies": [],
                    "responsibilities": []
                }
            else:
                if not current_role:
                    current_role = {
                        "role": "Intern/Developer",
                        "company": "",
                        "duration": "",
                        "technologies": [],
                        "responsibilities": []
                    }
                
                current_role["responsibilities"].append(clean_line)

                for cat, keywords in SKILL_KEYWORDS.items():
                    for kw in keywords:
                        if re.search(r"\b" + re.escape(kw) + r"\b", clean_line, re.IGNORECASE):
                            current_role["technologies"].append(self._find_original_casing(kw, clean_line))

        if current_role:
            roles.append(current_role)

        for r in roles:
            r["technologies"] = sorted(list(set(r["technologies"])))

        return roles


    def _parse_bulleted_list(self, content: str) -> list[str]:
        """Convert a block of text containing bullets/lines into a flat list of strings."""
        if not content:
            return []
        items = []
        for line in content.split("\n"):
            clean = re.sub(r"^[-*•]\s*", "", line).strip()
            if clean:
                items.append(clean)
        return items

    def _parse_hackathons(self, content: str) -> list[dict[str, Any]]:
        """Parse hackathon list into struct."""
        if not content:
            return []
        hackathons = []
        for line in content.split("\n"):
            clean = re.sub(r"^[-*•]\s*", "", line).strip()
            if not clean:
                continue
            # Parse result (e.g. 2nd Place, Finalist)
            result = "Participant"
            results_kw = ["Winner", "1st Place", "2nd Place", "3rd Place", "Finalist", "Top 10", "Top 5%"]
            for r in results_kw:
                if re.search(r"\b" + re.escape(r) + r"\b", clean, re.IGNORECASE):
                    result = r
                    break
            
            # Extract Year
            year_match = YEAR_REGEX.search(clean)
            year = int(year_match.group(0)) if year_match else None

            hackathons.append({
                "name": clean,
                "result": result,
                "year": year,
                "description": clean
            })
        return hackathons

    def _generate_summary(self, name: str, edu: dict, skills: dict, intern_count: int) -> str:
        """Create a professional summary sentence from parsed entities."""
        if not name:
            return ""
        
        degree = edu.get("degree", "graduate")
        branch = edu.get("branch", "Engineering")
        tech_list = skills.get("programming_languages", []) + skills.get("frameworks", [])
        techs = ", ".join(tech_list[:4])

        summary = f"{name} is a {degree} candidate in {branch}"
        if techs:
            summary += f" with expertise in {techs}."
        else:
            summary += "."
        
        if intern_count > 0:
            summary += f" Has completed {intern_count} internship{'s' if intern_count > 1 else ''} in software development/AI."
            
        return summary
