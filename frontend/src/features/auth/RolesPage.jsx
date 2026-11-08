import { useState } from "react";
import { Info, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useChoices } from "../../lib/api/useResources.js";
import { API } from "../../lib/api/endpoints.js";
import { AdminPagination } from "../../components/DataTable.jsx";
import { QueryState } from "../../components/QueryState.jsx";

const SYSTEM_ROLES = new Set(["quan_tri_vien", "quan_ly", "nhan_vien"]);

export function RolesPage() {
  const roles = useChoices(API.roles);
  const [searchDraft, setSearchDraft] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const allRoles = roles.data || [];
  const filtered = allRoles.filter((role) => {
    if (!searchTerm) return true;
    const keyword = searchTerm.toLowerCase();
    return (
      String(role.ten_vai_tro || "")
        .toLowerCase()
        .includes(keyword) ||
      String(role.ma_vai_tro || "")
        .toLowerCase()
        .includes(keyword) ||
      String(role.mo_ta || "")
        .toLowerCase()
        .includes(keyword)
    );
  });

  const totalPages = Math.max(Math.ceil(filtered.length / pageSize), 1);
  const currentPage = Math.min(page, totalPages);
  const rows = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="admin-screen">
      <div className="admin-page-heading">
        <h1>Quản lý vai trò</h1>
      </div>

      <div className="admin-toolbar">
        <form
          className="admin-toolbar-filters"
          onSubmit={(event) => {
            event.preventDefault();
            setSearchTerm(searchDraft.trim());
            setPage(1);
          }}
        >
          <div className="admin-input-shell admin-search-box">
            <Search size={18} aria-hidden="true" />
            <input
              type="search"
              aria-label="Tìm vai trò"
              placeholder="Tìm vai trò"
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
            />
          </div>
        </form>

        <button type="button" className="btn btn-primary admin-primary-cta">
          <Plus size={20} strokeWidth={2.25} aria-hidden="true" />
          <span>Tạo vai trò</span>
        </button>
      </div>

      <section className="admin-surface admin-table-card">
        <QueryState query={roles}>
          <div className="table-scroll admin-table-wrap">
            <table className="admin-table">
              <caption className="sr-only">Danh sách vai trò</caption>
              <thead>
                <tr>
                  <th scope="col" className="admin-col-stt">
                    STT
                  </th>
                  <th scope="col">Tên vai trò</th>
                  <th scope="col">Mô tả</th>
                  <th scope="col" className="admin-col-actions">
                    Thao tác
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.length ? (
                  rows.map((role, index) => {
                    const stt = String((currentPage - 1) * pageSize + index + 1).padStart(2, "0");
                    const isSystemRole = SYSTEM_ROLES.has(role.ma_vai_tro);
                    return (
                      <tr key={role.id}>
                        <td className="admin-col-stt">{stt}</td>
                        <td>
                          <strong>{role.ten_vai_tro}</strong>
                        </td>
                        <td className="admin-role-desc">{role.mo_ta || "—"}</td>
                        <td className="admin-col-actions">
                          <div className="admin-row-actions">
                            <button
                              type="button"
                              className={`admin-action-btn ${
                                isSystemRole ? "admin-action-muted" : ""
                              }`.trim()}
                              disabled={isSystemRole}
                              aria-label={`Sửa ${role.ten_vai_tro}`}
                            >
                              <Pencil size={15} aria-hidden="true" />
                              <span>Sửa</span>
                            </button>
                            <button
                              type="button"
                              className={`admin-action-btn ${
                                isSystemRole ? "admin-action-muted" : "admin-action-danger"
                              }`}
                              disabled={isSystemRole}
                              aria-label={`Xóa ${role.ten_vai_tro}`}
                            >
                              <Trash2 size={15} aria-hidden="true" />
                              <span>Xóa</span>
                            </button>
                            {isSystemRole && (
                              <span
                                className="admin-role-lock-info"
                                aria-label="Vai trò mặc định của hệ thống"
                              >
                                <Info size={18} aria-hidden="true" />
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={4} className="empty-state">
                      Chưa có dữ liệu phù hợp.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <AdminPagination
            page={currentPage}
            pageSize={pageSize}
            totalPages={totalPages}
            busy={roles.isFetching}
            onPage={setPage}
            onPageSize={(nextSize) => {
              setPageSize(nextSize);
              setPage(1);
            }}
          />
        </QueryState>
      </section>
    </div>
  );
}
