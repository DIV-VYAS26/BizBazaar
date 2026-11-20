"""Register all tables in one metadata registry for CLI, migrations and application use."""

from . import commerce  # noqa: F401 - import registers commerce/account tables
from .models import Base

__all__ = ["Base"]
