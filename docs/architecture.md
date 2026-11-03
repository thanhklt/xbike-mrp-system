# xBike MRP System Architecture

## 1. Executive Summary & Philosophy

The **xBike MRP System** is designed as a **Modular Monolith** optimized for bicycle assembly and manufacturing. The modular architecture provides high cohesion within manufacturing domains while keeping cognitive load and deployment friction low. If scale requires it, modules can be isolated into microservices along their clear domain boundaries.

```
       [ Client Applications (React SPA / Mobile) ]
                            │
                      [ Nginx Proxy ]
                            │
               [ FastAPI Modular Monolith ]
   ┌────────────────────────┼────────────────────────┐
   ▼                        ▼                        ▼
[Core & Cross-Cutting]  [Domain Modules]        [Shared Utilities]
- Config                - Catalog & Suppliers   - Enums & Units
- Security & JWT        - Multi-level BOM       - Pagination
- Logging & Tracing     - Inventory & Warehouse - DTO base models
- Exception handling    - Work Orders & Assembly
                        - Material Issuance
                        - Receiving & Audit
                            │
              [ PostgreSQL 16 (Relational DB) ]
```

---

## 2. Core Manufacturing & MRP Lifecycle

In bicycle manufacturing, a finished product (e.g., *xBike Urban E-Commuter*) is composed of complex sub-assemblies (e.g., *Front Wheel Assembly*, *Drivetrain System*, *Frame & Fork Kit*) which in turn comprise raw components (spokes, rims, hubs, bearings, bolts).

The manufacturing lifecycle executes in distinct, auditable phases:

```
[1. Demand & Sales Plan]
         │
         ▼
[2. BOM Explosion & MRP Run] ──▶ Identifies Gross vs. Net Component Requirements
         │
         ├───▶ [3a. Purchase Orders (PO)] ──▶ [Receiving & Inspection] ──▶ [Stock on Hand]
         │
         └───▶ [3b. Work Orders (WO)] ────▶ [Material Issuing / Pick] ──▶ [Shop Floor Assembly]
                                                                                │
                                                                                ▼
[5. Sales & Logistics] ◀── [Finished Goods Issuing] ◀── [Inspection & QA Pass]
```

### Domain Module Breakdown

| Module | Responsibility | Key Entities |
| :--- | :--- | :--- |
| **`auth`** | JWT issuance/validation and orchestration through the employee public service. Contains router.py, schema.py and service.py. | `AuthService` |
| **`nhan_vien`** | Owns employee credentials, profiles and roles; public authentication and atomic password-change operations. | `NhanVien`, `VaiTro`, `NhanVienService` |
| **`mat_hang`** | Owns item master data, soft delete and the application item snapshot. Serves `/mat_hang` and `/danh_muc_mat_hang/`. | `MatHang`, `MatHangReader`, `MatHangService` |
| **`suppliers`** | Approved vendor list (AVL), vendor lead times, pricing tiers. | `Supplier`, `SupplierPartPricing` |
| **`bom`** | Multi-level Bill of Materials trees with scrap factor and revisions. | `BOMHeader`, `BOMItem`, `BOMRevision` |
| **`inventory`** | Real-time stock levels across bins, lots, and movement ledger. | `StockLevel`, `Warehouse`, `BinLocation`, `StockMovement` |
| **`receiving`** | Inbound logistics, goods receipt notes (GRN), lot tracking. | `GoodsReceiptNote`, `ReceiptItem` |
| **`material_issuing`** | Staging and issuance of required components for active work orders. | `MaterialIssueRequest`, `PickList`, `IssueItem` |
| **`san_xuat`** | Production requests, deterministic planning, saved order trees and atomic cancellation. Nine request endpoints; order/completion endpoints remain future work. | `YeuCauSanXuat`, `LenhSanXuat`, `ChiTietLenhSanXuat`, `ChungTuHoanThanhSx` |
| **`phieu_xuat`** | Internal issue totals and cancellation of unposted documents; caller owns the transaction. No endpoints yet. | `PhieuXuat`, `ChiTietPhieuXuat`, `PhieuXuatSanXuatService` |
| **`finished_goods_issuing`** | Shipping / transferring completed bicycles to distribution. | `DispatchOrder`, `DispatchItem` |
| **`reporting`** | MRP calculation engines, inventory valuation, scrap & lead-time analytics. | `MRPRunRecord`, `MaterialShortageReport` |
| **`audit`** | Append/read history through its public service; SQL trigger rejects changes to persisted history. | `LichSuThaoTac`, `AuditService` |

---

## 3. Database & Transactional Integrity

### Production requests (03/11/2026)

`san_xuat` serves the nine `/yeu_cau_san_xuat` endpoints from contract v3 §8. Its service
uses persistence/employee/BOM/issue ports and the public `MatHangStockReader`; composition
binds every adapter to the same session. `NhanVienService` validates the assignee, the
item availability service reads stock directly from DB, and `BomPlanningReader` exposes
the current graph and the shared BOM advisory lock. No stock cache drives planning.

Preview consumes semi-finished stock across BFS branches without reserving it. Submission
locks the request, validates If-Match, assignee and a ten-minute signed preview token,
then saves parent-first orders and direct-demand snapshots. Material shortages produce
`cho_bo_sung_vat_tu`; sufficient materials produce `da_gui`. Existing finished stock can
satisfy the request without orders. Orders start as drafts with no assigned executor.

Cancellation locks related documents, rejects posted dependencies and cancels children
before parents. Draft issues/completions are deleted; pending ones become rejected with
the reason in audit. Domain writes and audit commit together; none of these operations
changes stock or ledger. Employee reads use FOR SHARE; item locks are ordered by ID;
submission holds the same advisory transaction lock as BOM mutation.

The six production/issue ORM tables match bootstrap, while other warehouse mappings remain
legacy. Four `/production/work-orders` routes are removed. Frontend migration, order and
completion APIs, issue APIs, and receipt-triggered material rechecks are separate tasks.
See [sequences](sequence/san_xuat.md) and D-SX-01–19. Rollback must restore the related
router/composition/model/FK changes together; it must preserve already-created documents.

### Auth, employee and audit boundary (30/10/2026)

`AuthService` imports the employee module's public service and exported DTOs. It never imports employee ORM/repositories. `NhanVienService` verifies credentials and current account/role/password version, returns a safe `AuthIdentity`, and owns the password-change transaction. The ORM objects and hashes remain inside the employee module.

Password changes call `AuditService.append` with the same request session; the audit service never commits independently. `SELECT FOR UPDATE` refreshes credentials under lock before verification, and password UPDATE plus audit INSERT commit together. Existing JWTs fail the keyed password-version check after a password change.

Only the three tables `"NhanVien"`, `"VaiTro"`, `"LichSuThaoTac"` have been renamed to PascalCase. Other models only receive FK target updates where necessary; their remaining SQL v4 drift is outside this task. Demo Docker uses bootstrap on a fresh data directory, without migrations. The manufacturing overview below describes broader architecture, not proof that every workflow/schema has been implemented or verified.

- **ACID Guarantee**: Inventory adjustments and material issuance are wrapped in strict database transactions with row-level locks (`SELECT FOR UPDATE`) to prevent negative inventory allocations.
- **Double-Entry Stock Ledger**: Physical stock changes are recorded as ledger movements (Credit from Location A, Debit to Location B) rather than arbitrary in-place mutations.
- **Audit Trails**: All status transitions (`DRAFT` -> `PLANNED` -> `RELEASED` -> `IN_PROGRESS` -> `COMPLETED`) generate immutable audit records.


### Employee administration (01/11/2026)

The employee module contains models.py, router.py, schemas.py, ports.py, repository.py and service.py, plus __init__.py. DTOs needed internally live in schemas.py; NhanVienService owns reads and mutations through NhanVienRepository. The former dto.py, write_service.py and module errors.py have been consolidated. Auth still calls only the public employee service; audit writes go through AuditService in the same transaction.

The eight employee/role endpoints are documented in [sequence diagrams](sequence/nhan_vien.md). DELETE reversibly blocks an account with a required JSON reason and replaces POST /vo_hieu_hoa. POST /mo_khoa restores activity. Documents, roles and history are retained; list queries still support blocked accounts and status filtering.

One administrator is provisioned by bootstrap. APIs reject creation/promotion of another admin, demotion of the existing admin and blocking that admin. Mutations lock and refresh the administrator row before locking the target and comparing If-Match. The API rechecks account/role/password version after waiting. No singleton-admin database constraint is added; direct SQL is outside this API policy.

Employee changes and audit commit/rollback together. Role changes append thu_hoi_quyen and cap_quyen; DELETE appends vo_hieu_hoa; unlock appends sua with reason and before/after data. Account/role errors use the contract-v2 error/meta envelope, matching auth. Other modules retain their existing error envelopes.


## Phạm vi mặt hàng đã triển khai ngày 01/11/2026

`mat_hang` là chủ sở hữu duy nhất của bảng `"MatHang"` theo `infra/postgres/init.sql`. Dữ liệu tồn đã nằm trong `so_luong_ton` và `ton_kho_updated_at`; module không tạo/xóa dòng ton_kho. Các module còn mapping tồn kho cũ được giữ cho tác vụ sau, không phải một schema thay thế.

Router có sáu endpoint; ba GET mặt hàng đọc cùng snapshot bất biến nạp ở startup. Reader không có repository/session; auth vẫn kiểm tra danh tính hiện hành trong DB. Command service dùng repository + AuditService + transaction và công bố cache sau commit. Adapter synchronizer dùng listener riêng, LISTEN trước initial load, refresh nguyên tử, reconnect và đối soát 30 giây. Giới hạn nhất quán tức thời là một worker; đa worker đồng bộ bất đồng bộ.

Soft delete giữ dữ liệu/quan hệ/số dư, và GET vẫn trả hàng bị khóa. Các service tạo BOM/phiếu/lệnh hiện có gọi public MatHangAvailabilityService trong transaction của caller, khóa dòng để ngăn tranh chấp với vô hiệu hóa. Không thêm endpoint yêu cầu sản xuất hoặc chuyển đổi ORM của các module cũ trong tác vụ này. Xem [sequence](sequence/mat_hang.md) và [plan/giới hạn](plans/2026-11-01-hop-nhat-mat-hang.md).
