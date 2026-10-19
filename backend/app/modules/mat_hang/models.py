"""ORM model for mat_hang.

Reuses the mapped Part entity from catalog module to preserve single Declarative table registration.
"""

from app.modules.catalog.models import Part as MatHang

__all__ = ["MatHang"]
