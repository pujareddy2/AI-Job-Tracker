"""
utils/__init__.py
-----------------
Makes `utils` a Python package.

The utilities package contains shared, reusable helper modules that are
imported by multiple other packages (scrapers, filters, notifiers, etc.).

Keeping utilities in their own package prevents circular imports and
encourages the single-responsibility principle — each utility module
does exactly one thing well.
"""
