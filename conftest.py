"""
Pytest configuration.

This file lives at the project root so pytest adds the root to sys.path before
collecting tests. That lets `import tools` (and other top-level modules) work no
matter how the suite is launched — `pytest`, `pytest tests/test_tools.py`, etc.
"""
