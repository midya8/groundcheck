"""GroundCheck: offline grounding checks for answers against sources."""

from .check import check_grounding
from .sources import load_sources

__version__ = "0.1.0"
__all__ = ["check_grounding", "load_sources", "__version__"]
