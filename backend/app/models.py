"""Register all mapped models, including when Alembic loads metadata."""

from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.bom import models as bom_models  # noqa: F401
from app.modules.catalog import models as catalog_models  # noqa: F401
from app.modules.inventory import models as inventory_models  # noqa: F401
from app.modules.material_issuing import models as material_issuing_models  # noqa: F401
from app.modules.nha_cung_cap import models as suppliers_models  # noqa: F401
from app.modules.production import models as production_models  # noqa: F401
from app.modules.receiving import models as receiving_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401
