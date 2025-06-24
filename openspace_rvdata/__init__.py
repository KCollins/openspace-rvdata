"""init.py"""

from importlib import metadata

from openspace_rvdata.r2r2df import get_r2r_url  # noqa F401

# Set version
__version__ = metadata.version('openspace_rvdata')