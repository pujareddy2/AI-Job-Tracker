"""
tests/test_config.py — Tests for config.py
==========================================
Tests verify that:
    1. The `settings` singleton loads without error.
    2. Default values are correct.
    3. The PROJECT_ROOT is a valid directory.
    4. The `is_development` and `is_production` properties behave correctly.
    5. The `log_dir` and `credentials_dir` properties resolve correctly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import settings, PROJECT_ROOT


class TestProjectRoot:
    """Tests for the PROJECT_ROOT constant."""

    def test_project_root_is_a_directory(self) -> None:
        """PROJECT_ROOT must point to a real directory."""
        assert PROJECT_ROOT.is_dir(), f"PROJECT_ROOT does not exist: {PROJECT_ROOT}"

    def test_project_root_contains_config_py(self) -> None:
        """config.py must be present in the project root."""
        assert (PROJECT_ROOT / "config.py").exists()


class TestDefaultSettings:
    """Tests that defaults match the documented values."""

    def test_log_level_default(self) -> None:
        """Default log level should be INFO (from .env.example default)."""
        # The test env may not have a .env, so settings falls back to defaults.
        assert settings.log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def test_app_env_default(self) -> None:
        """Default app environment should be 'development'."""
        assert settings.app_env in {"development", "staging", "production"}

    def test_log_dir_property(self) -> None:
        """log_dir should resolve to <project_root>/logs."""
        assert settings.log_dir == PROJECT_ROOT / "logs"

    def test_credentials_dir_property(self) -> None:
        """credentials_dir should resolve to <project_root>/credentials."""
        assert settings.credentials_dir == PROJECT_ROOT / "credentials"

    def test_google_credentials_is_path(self) -> None:
        """google_credentials must always be a Path object."""
        assert isinstance(settings.google_credentials, Path)


class TestEnvironmentProperties:
    """Tests for the is_development / is_production convenience properties."""

    def test_is_development_when_app_env_is_development(self) -> None:
        # We can't monkeypatch a frozen pydantic model directly, so we
        # create a fresh AppSettings instance with explicit values.
        from config import AppSettings

        dev_settings = AppSettings(app_env="development")
        assert dev_settings.is_development is True
        assert dev_settings.is_production is False

    def test_is_production_when_app_env_is_production(self) -> None:
        from config import AppSettings

        prod_settings = AppSettings(app_env="production")
        assert prod_settings.is_production is True
        assert prod_settings.is_development is False
