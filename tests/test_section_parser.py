"""
tests/test_section_parser.py — Unit Tests for resume_parser/section_parser.py
=============================================================================
Tests verify (no network, uses structured strings):
  1. Section splits based on standard headers.
  2. Personal info extraction (name, email, phone, linkedin, github, portfolio).
  3. Coding profiles (leetcode, hackerrank).
  4. Education details (degree, branch, cgpa, grad year, expected).
  5. Skills classification from text context into categories.
  6. Internship/Experience list extraction.
  7. Projects list extraction.
"""

from __future__ import annotations

import pytest

from resume_parser.section_parser import SectionParser


@pytest.fixture()
def sample_resume_text() -> str:
    return """
MIDDE SRAVYA
Email: middepuja1005@gmail.com | Phone: +91-9876543210
LinkedIn: linkedin.com/in/sravya-midde | GitHub: github.com/sravya-midde
Location: Hyderabad, India | LeetCode: leetcode.com/sravya_midde | Portfolio: sravya-midde.github.io

EDUCATION
B.Tech in Computer Science and Engineering
JNTUH, Hyderabad
CGPA: 9.1 / 10 | Expected Graduation: May 2027

SKILLS
Programming Languages: Python, JavaScript, SQL
Frameworks & Libraries: FastAPI, LangChain, React.js, NumPy
Databases: PostgreSQL, ChromaDB
Cloud: AWS, Docker

EXPERIENCE
AI Engineering Intern | TechCorp, Hyderabad | June 2025 - August 2025
- Built a RAG pipeline using LangChain and ChromaDB
- Implemented FastAPI endpoints
- Technologies: Python, FastAPI, LangChain, ChromaDB

PROJECTS
AI Job Tracker
- Automated resume parsing and job relevance scoring
- Technologies: Python, LangChain, Google Sheets API
"""


def test_personal_info_extraction(sample_resume_text: str) -> None:
    parser = SectionParser()
    parsed = parser.parse(sample_resume_text)
    personal = parsed["personal"]

    assert personal["name"] == "MIDDE SRAVYA"
    assert personal["email"] == "middepuja1005@gmail.com"
    assert personal["phone"] == "+91-9876543210"
    assert personal["linkedin"] == "linkedin.com/in/sravya-midde"
    assert personal["github"] == "github.com/sravya-midde"
    assert personal["portfolio"] == "sravya-midde.github.io"
    assert personal["location"] == "Hyderabad"
    assert personal["coding_profiles"]["leetcode"] == "leetcode.com/sravya_midde"


def test_education_parsing(sample_resume_text: str) -> None:
    parser = SectionParser()
    parsed = parser.parse(sample_resume_text)
    edu = parsed["education"]

    assert edu["degree"] == "B.Tech"
    assert edu["branch"] == "Computer Science"
    assert "JNTUH" in edu["institution"]
    assert "9.1" in edu["cgpa"]
    assert edu["graduation_year"] == 2027
    assert edu["expected"] is True


def test_skills_parsing(sample_resume_text: str) -> None:
    parser = SectionParser()
    parsed = parser.parse(sample_resume_text)
    skills = parsed["skills"]

    assert "Python" in skills["programming_languages"]
    assert "FastAPI" in skills["frameworks"]
    assert "LangChain" in skills["libraries"]
    assert "PostgreSQL" in skills["databases"]
    assert "ChromaDB" in skills["databases"]
    assert "AWS" in skills["cloud"]
    assert "Docker" in skills["cloud"]


def test_experience_parsing(sample_resume_text: str) -> None:
    parser = SectionParser()
    parsed = parser.parse(sample_resume_text)
    exp = parsed["experience"]

    assert exp["level"] == "Intern"
    assert exp["internship_count"] == 1
    assert len(exp["internships"]) == 1
    
    internship = exp["internships"][0]
    assert "TechCorp" in internship["company"]
    assert "AI Engineering Intern" in internship["role"]
    assert "FastAPI" in internship["technologies"]
    assert "LangChain" in internship["technologies"]


def test_projects_parsing(sample_resume_text: str) -> None:
    parser = SectionParser()
    parsed = parser.parse(sample_resume_text)
    projects = parsed["projects"]

    assert len(projects) == 1
    proj = projects[0]
    assert "AI Job Tracker" in proj["name"]
    assert "LangChain" in proj["technologies"]
    assert "Automated resume parsing" in proj["description"]
