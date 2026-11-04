"""Register all mapped models, including when Alembic loads metadata."""

from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.bom import models as bom_models  # noqa: F401
from app.modules.inventory import models as inventory_models  # noqa: F401
from app.modules.lenh_san_xuat import models as lenh_san_xuat_models  # noqa: F401
from app.modules.mat_hang import models as mat_hang_models  # noqa: F401
from app.modules.nha_cung_cap import models as nha_cung_cap_models  # noqa: F401
from app.modules.nhan_vien import models as nhan_vien_models  # noqa: F401
from app.modules.phieu_nhap import models as phieu_nhap_models  # noqa: F401
from app.modules.phieu_xuat import models as phieu_xuat_models  # noqa: F401
from app.modules.san_xuat import models as san_xuat_models  # noqa: F401
