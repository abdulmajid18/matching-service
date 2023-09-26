"""
Specifies code to execute before running tests.
"""

import os

# This switches environments to use test database.
os.environ["ENVIRONMENT"] = "PYTEST"
