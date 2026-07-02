# docs/coding_standards.md — Coding Standards

## 1. Formatting

| Rule | Tool | Setting |
|---|---|---|
| Max line length | ruff | 100 characters |
| Quote style | ruff | double quotes |
| Import sorting | ruff (isort) | stdlib → third-party → local |

Run the formatter:
```bash
ruff format .
ruff check . --fix
```

## 2. Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Modules / files | `snake_case` | `base_scraper.py` |
| Classes | `PascalCase` | `LinkedInScraper` |
| Functions / methods | `snake_case` | `get_logger()` |
| Constants | `UPPER_SNAKE_CASE` | `PROJECT_ROOT` |
| Private helpers | `_leading_underscore` | `_build_session()` |
| Type aliases | `PascalCase` | `JobDict = dict[str, Any]` |

## 3. Type Hints

- All public functions and methods **must** have complete type annotations.
- Use `from __future__ import annotations` at the top of every module to
  enable postponed evaluation of annotations (PEP 563).
- Prefer built-in generics (`list[str]`, `dict[str, Any]`) over `typing.List`.
- Use `X | None` instead of `Optional[X]` (Python 3.10+ style).

## 4. Docstrings

Follow **NumPy-style** docstrings for all public classes and functions:

```python
def scrape(self, keyword: str, location: str) -> list[dict[str, Any]]:
    """
    One-line summary ending with a period.

    Extended description if needed.

    Parameters
    ----------
    keyword : str
        Job title or skill to search for.
    location : str
        Geographic location or "Remote".

    Returns
    -------
    list[dict[str, Any]]
        List of raw job dictionaries.

    Raises
    ------
    ScraperError
        If the request fails after all retry attempts.
    """
```

## 5. Error Handling

- Raise specific custom exceptions from `utils/exceptions.py`.
- Always pass structured context as keyword args: `raise ScraperError("msg", url=url)`.
- Use the `@retry` decorator from `utils/helpers.py` for network calls.
- Never swallow exceptions silently — log at minimum WARNING level.

## 6. Logging

- Import: `from utils.logger import get_logger; logger = get_logger(__name__)`.
- Use structured `extra` dicts: `logger.info("msg", extra={"key": value})`.
- Choose the right level:
  - `DEBUG` — detailed tracing, disabled in production.
  - `INFO` — normal operations, pipeline step completions.
  - `WARNING` — recoverable issues (retry triggered, empty result set).
  - `ERROR` — failure that impacts the current run.
  - `CRITICAL` — unrecoverable failure, immediate alert required.

## 7. Testing

- Every module has a corresponding test file: `tests/test_<module>.py`.
- Use `pytest` markers: `@pytest.mark.unit`, `@pytest.mark.integration`.
- Mock external services in unit tests; never hit real APIs in CI.
- Maintain ≥ 80% line coverage (enforced by `--cov` in pytest config).

## 8. Git Conventions

- Commit message format: `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`
  - Example: `feat(scraper): add LinkedIn pagination`
- Branch names: `feature/<short-name>` or `fix/<short-name>`
- Never push directly to `main` — use pull requests.
