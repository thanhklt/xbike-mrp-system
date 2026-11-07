import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  Ban,
  Calendar,
  CirclePercent,
  Eye,
  Info,
  KeyRound,
  Layers,
  LockOpen,
  Mail,
  Pencil,
  Phone,
  Plus,
  Search,
  UserRound,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { API } from "../../lib/api/endpoints.js";
import { readResource, writeResource } from "../../lib/api/client.js";
import { useChoices, useCollection, useDetail, useWrite } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import {
  ROLE_LABELS,
  STATUS_LABELS,
  formatCoefficient,
  formatDate,
  initials,
  nullable,
} from "../../lib/format.js";
import { useAuth } from "./AuthProvider.jsx";
import { AdminPagination } from "../../components/DataTable.jsx";
import { RecordPanel } from "../../components/RecordPanel.jsx";
import { AdminRoleBadge, AdminStatusBadge, Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import { ErrorNotice, QueryState, Notice } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";

const base = "/admin/tai-khoan";

function promptAccountStateChange({ record, etag, currentUserId, confirm, notify, queryClient, onError }) {
  if (!record) return;
  if (record.ma_vai_tro === "quan_tri_vien" || record.id === currentUserId) {
    return;
  }
  if (!etag) {
    onError?.({
      message: "Chưa tải được phiên bản dữ liệu để xác nhận. Vui lòng tải lại.",
    });
    return;
  }
  const unlock = record.trang_thai === "bi_khoa";
  confirm({
    title: unlock ? "Mở khóa tài khoản" : "Khóa tài khoản",
    description: `${record.ma_nhan_vien} · ${record.ho_ten || record.ten_dang_nhap}`,
    reason: true,
    danger: !unlock,
    impact:
      "Bảo toàn hồ sơ, công việc và chứng từ đã lập. Khóa tài khoản chặn mọi request tiếp theo.",
    onConfirm: async (reason) => {
      await writeResource({
        path: `${API.employees}/${record.id}${unlock ? "/mo_khoa" : ""}`,
        method: unlock ? "post" : "delete",
        body: { ly_do: reason },
        etag,
      });
      await queryClient.invalidateQueries({ queryKey: ["resources"] });
      notify(unlock ? "Đã mở khóa tài khoản." : "Đã khóa tài khoản.");
    },
  });
}

export function UsersPage() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const isCreate = id === "moi";
  const isDetail = Boolean(id && !isCreate);
  const isEditing = searchParams.get("mode") === "edit";
  const roles = useChoices(API.roles);

  if (isDetail) {
    return (
      <AccountDetailView
        id={id}
        roles={roles}
        isEditing={isEditing}
        onStartEdit={() => setSearchParams({ mode: "edit" })}
        onCancelEdit={() => setSearchParams({})}
      />
    );
  }

  return <AccountListView id={id} roles={roles} />;
}

function AccountListView({ id, roles }) {
  const { user } = useAuth();
  const { confirm, notify } = useFeedback();
  const queryClient = useQueryClient();
  const collection = useCollection(API.employees, { page: 1, page_size: 10, sort: "id" });
  const detail = useDetail(API.employees, id);
  const [searchDraft, setSearchDraft] = useState(collection.params.q || "");
  const [selectedIds, setSelectedIds] = useState([]);
  const [loadingRowId, setLoadingRowId] = useState(null);
  const [rowError, setRowError] = useState(null);

  const rows = collection.query.data?.data || [];
  const meta = collection.query.data?.meta || {};
  const page = meta.page || collection.params.page || 1;
  const pageSize = meta.page_size || collection.params.page_size || 10;
  const totalPages = meta.total_pages || 1;
  const currentIds = rows.map((row) => row.id);
  const allCurrentSelected =
    currentIds.length > 0 && currentIds.every((rowId) => selectedIds.includes(rowId));

  useEffect(() => {
    setSelectedIds([]);
  }, [
    collection.params.page,
    collection.params.page_size,
    collection.params.q,
    collection.params.vai_tro_id,
    collection.params.trang_thai,
  ]);

  function toggleAll(checked) {
    setSelectedIds(checked ? currentIds : []);
  }

  function toggleRow(rowId, checked) {
    setSelectedIds((previous) =>
      checked ? [...new Set([...previous, rowId])] : previous.filter((item) => item !== rowId),
    );
  }

  async function handleRowStateAction(row) {
    if (loadingRowId !== null) return;
    setRowError(null);
    setLoadingRowId(row.id);
    try {
      const snapshot = await readResource(`${API.employees}/${row.id}`);
      const freshRecord = snapshot?.data || row;
      if (freshRecord.ma_vai_tro === "quan_tri_vien" || freshRecord.id === user.id) {
        await queryClient.invalidateQueries({ queryKey: ["resources"] });
        return;
      }
      promptAccountStateChange({
        record: freshRecord,
        etag: snapshot?.etag,
        currentUserId: user.id,
        confirm,
        notify,
        queryClient,
        onError: setRowError,
      });
    } catch (failure) {
      setRowError(failure);
    } finally {
      setLoadingRowId(null);
    }
  }

  return (
    <div className="admin-screen">
      <div className="admin-page-heading">
        <h1>Quản lý tài khoản</h1>
      </div>

      <div className="admin-toolbar">
        <form
          className="admin-toolbar-filters"
          onSubmit={(event) => {
            event.preventDefault();
            collection.filter({ q: searchDraft.trim() });
          }}
        >
          <div className="admin-input-shell admin-search-box">
            <Search size={18} aria-hidden="true" />
            <input
              type="search"
              aria-label="Tìm tài khoản"
              placeholder="Tìm tài khoản"
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
            />
          </div>

          <div className="admin-select-shell">
            <Layers size={18} aria-hidden="true" />
            <select
              aria-label="Vai trò"
              value={collection.params.vai_tro_id ?? ""}
              onChange={(event) => collection.filter({ vai_tro_id: event.target.value })}
            >
              <option value="">Vai trò</option>
              {(roles.data || []).map((role) => (
                <option key={role.id} value={role.id}>
                  {ROLE_LABELS[role.ma_vai_tro] || role.ten_vai_tro}
                </option>
              ))}
            </select>
          </div>

          <div className="admin-select-shell">
            <Activity size={18} aria-hidden="true" />
            <select
              aria-label="Trạng thái"
              value={collection.params.trang_thai ?? ""}
              onChange={(event) => collection.filter({ trang_thai: event.target.value })}
            >
              <option value="">Trạng thái</option>
              {["hoat_dong", "bi_khoa"].map((value) => (
                <option key={value} value={value}>
                  {STATUS_LABELS[value]}
                </option>
              ))}
            </select>
          </div>
        </form>

        <Link className="btn btn-primary admin-primary-cta" to={`${base}/moi`}>
          <Plus size={20} strokeWidth={2.25} aria-hidden="true" />
          <span>Tạo tài khoản</span>
        </Link>
      </div>

      <ErrorNotice error={rowError} />

      <section className="admin-surface admin-table-card">
        <QueryState query={collection.query}>
          <div className="table-scroll admin-table-wrap">
            <table className="admin-table">
              <caption className="sr-only">Danh sách tài khoản</caption>
              <thead>
                <tr>
                  <th scope="col" className="admin-col-check">
                    <input
                      type="checkbox"
                      aria-label="Chọn tất cả tài khoản trên trang"
                      checked={allCurrentSelected}
                      disabled={rows.length === 0}
                      onChange={(event) => toggleAll(event.target.checked)}
                    />
                  </th>
                  <th scope="col" className="admin-col-stt">
                    STT
                  </th>
                  <th scope="col">Tên</th>
                  <th scope="col">Ngày sinh</th>
                  <th scope="col">Vai trò</th>
                  <th scope="col">Trạng thái</th>
                  <th scope="col" className="admin-col-actions">
                    Thao tác
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.length ? (
                  rows.map((row, index) => {
                    const stt = String((page - 1) * pageSize + index + 1).padStart(2, "0");
                    const displayName = row.ho_ten || "Chưa có họ tên";
                    const lockedAdmin = row.ma_vai_tro === "quan_tri_vien";
                    const canChangeState = !lockedAdmin && row.id !== user.id;
                    const isLocked = row.trang_thai === "bi_khoa";
                    return (
                      <tr key={row.id}>
                        <td className="admin-col-check">
                          <input
                            type="checkbox"
                            aria-label={`Chọn ${row.ma_nhan_vien}`}
                            checked={selectedIds.includes(row.id)}
                            onChange={(event) => toggleRow(row.id, event.target.checked)}
                          />
                        </td>
                        <td className="admin-col-stt">{stt}</td>
                        <td>
                          <div className="admin-user-cell">
                            <span className="admin-avatar-circle" aria-hidden="true">
                              {initials(row.ho_ten || row.ten_dang_nhap)}
                            </span>
                            <div className="admin-user-meta">
                              <strong>{displayName}</strong>
                              <small>{row.ma_nhan_vien}</small>
                            </div>
                          </div>
                        </td>
                        <td>{formatDate(row.ngay_sinh)}</td>
                        <td>
                          <AdminRoleBadge role={row.ma_vai_tro} />
                        </td>
                        <td>
                          <AdminStatusBadge status={row.trang_thai} />
                        </td>
                        <td className="admin-col-actions">
                          <div className="admin-row-actions">
                            <Link
                              className="admin-action-btn"
                              to={`${base}/${row.id}`}
                              aria-label={`Chi tiết ${row.ma_nhan_vien}`}
                            >
                              <Eye size={15} aria-hidden="true" />
                              <span>Chi tiết</span>
                            </Link>
                            <Link
                              className="admin-action-btn"
                              to={`${base}/${row.id}?mode=edit`}
                              aria-label={`Sửa ${row.ma_nhan_vien}`}
                            >
                              <Pencil size={15} aria-hidden="true" />
                              <span>Sửa</span>
                            </Link>
                            <button
                              type="button"
                              className={`admin-action-btn ${
                                isLocked ? "admin-action-unlock" : "admin-action-danger"
                              }`}
                              disabled={!canChangeState || loadingRowId === row.id}
                              aria-label={`${isLocked ? "Mở khóa" : "Vô hiệu hóa"} ${row.ma_nhan_vien}`}
                              onClick={() => handleRowStateAction(row)}
                            >
                              {isLocked ? (
                                <LockOpen size={15} aria-hidden="true" />
                              ) : (
                                <Ban size={15} aria-hidden="true" />
                              )}
                              <span>{isLocked ? "Mở khóa" : "Vô hiệu hóa"}</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={7} className="empty-state">
                      Chưa có dữ liệu phù hợp.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <AdminPagination
            page={page}
            pageSize={pageSize}
            totalPages={totalPages}
            busy={collection.query.isFetching}
            onPage={collection.setPage}
            onPageSize={collection.setPageSize}
          />
        </QueryState>
      </section>

      <RecordPanel id={id} query={detail} base={base} title="Tạo tài khoản">
        {(snapshot) => (
          <QueryState query={roles}>
            <EmployeeForm snapshot={snapshot} roles={roles.data || []} />
          </QueryState>
        )}
      </RecordPanel>
    </div>
  );
}

function AccountDetailView({ id, roles, isEditing, onStartEdit, onCancelEdit }) {
  const { user } = useAuth();
  const { confirm, notify } = useFeedback();
  const queryClient = useQueryClient();
  const detail = useDetail(API.employees, id);
  const snapshot = detail.data;
  const record = snapshot?.data;
  const lockedAdmin = record?.ma_vai_tro === "quan_tri_vien";
  const canChangeState = record && !lockedAdmin && record.id !== user.id;
  const isLocked = record?.trang_thai === "bi_khoa";

  function handleToggleState() {
    if (!record) return;
    promptAccountStateChange({
      record,
      etag: snapshot?.etag,
      currentUserId: user.id,
      confirm,
      notify,
      queryClient,
    });
  }

  return (
    <div className="admin-screen">
      <div className="admin-page-heading">
        <h1>Chi tiết tài khoản</h1>
      </div>

      <div className="admin-detail-subbar">
        <Link className="admin-subbar-btn" to={base}>
          <ArrowLeft size={16} aria-hidden="true" />
          <span>Quay lại</span>
        </Link>
        {record && (
          <div className="admin-detail-actions">
            {isEditing ? (
              <button type="button" className="admin-subbar-btn" onClick={onCancelEdit}>
                <span>Xem chi tiết</span>
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary admin-primary-cta"
                onClick={onStartEdit}
              >
                <Pencil size={15} aria-hidden="true" />
                <span>Chỉnh sửa</span>
              </button>
            )}
            <button
              type="button"
              className={`admin-subbar-btn ${
                isLocked ? "admin-action-unlock" : "admin-action-danger"
              }`}
              disabled={!canChangeState}
              onClick={handleToggleState}
            >
              {isLocked ? (
                <LockOpen size={15} aria-hidden="true" />
              ) : (
                <Ban size={15} aria-hidden="true" />
              )}
              <span>{isLocked ? "Mở khóa" : "Vô hiệu hóa"}</span>
            </button>
          </div>
        )}
      </div>

      <QueryState query={detail}>
        {record && (
          <div className="admin-detail-grid" key={`${id}-${snapshot.etag || "read"}`}>
            <section className="admin-surface admin-identity-card">
              <div className="admin-identity-avatar" aria-hidden="true">
                {initials(record.ho_ten || record.ten_dang_nhap)}
              </div>
              <h2 className="admin-identity-name">{record.ho_ten || "Chưa có họ tên"}</h2>
              <p className="admin-identity-code">{record.ma_nhan_vien}</p>
              <hr className="admin-identity-divider" />
              <div className="admin-identity-badges">
                <AdminRoleBadge role={record.ma_vai_tro} />
                <AdminStatusBadge status={record.trang_thai} />
              </div>
            </section>

            <section className="admin-surface admin-info-card">
              <div className="admin-card-title">
                <Info size={18} className="admin-title-icon" aria-hidden="true" />
                <h2>Thông tin tài khoản</h2>
              </div>

              {isEditing ? (
                <QueryState query={roles}>
                  <EmployeeForm
                    snapshot={snapshot}
                    roles={roles.data || []}
                    onCancel={onCancelEdit}
                    onSaved={onCancelEdit}
                  />
                </QueryState>
              ) : (
                <dl className="admin-detail-rows">
                  <DetailRow icon={UserRound} label="Họ tên" value={record.ho_ten || "—"} />
                  <DetailRow
                    icon={Calendar}
                    label="Ngày sinh"
                    value={formatDate(record.ngay_sinh)}
                  />
                  <DetailRow
                    icon={Phone}
                    label="Số điện thoại"
                    value={record.so_dien_thoai || "—"}
                  />
                  <DetailRow icon={Mail} label="Email" value={record.email || "—"} />
                  <DetailRow
                    icon={UserRound}
                    label="Tên đăng nhập"
                    value={record.ten_dang_nhap || "—"}
                  />
                  <DetailRow icon={KeyRound} label="Mật khẩu" value="••••••••" />
                  <DetailRow
                    icon={Layers}
                    label="Vai trò"
                    value={ROLE_LABELS[record.ma_vai_tro] || record.ma_vai_tro || "—"}
                  />
                  <DetailRow
                    icon={Calendar}
                    label="Ngày vào làm"
                    value={formatDate(record.ngay_vao_lam)}
                  />
                  <DetailRow
                    icon={CirclePercent}
                    label="Hệ số lương"
                    value={formatCoefficient(record.he_so_luong)}
                  />
                  <DetailRow
                    icon={Activity}
                    label="Trạng thái"
                    value={<AdminStatusBadge status={record.trang_thai} />}
                    plain
                  />
                </dl>
              )}
            </section>
          </div>
        )}
      </QueryState>
    </div>
  );
}

function DetailRow({ icon, label, value, plain = false }) {
  const IconComponent = icon;
  return (
    <div className="admin-detail-row">
      <dt>
        <IconComponent size={18} aria-hidden="true" />
        <span>{label}</span>
      </dt>
      <dd className={plain ? "is-plain" : ""}>{value}</dd>
    </div>
  );
}

function EmployeeForm({ snapshot, roles, onCancel, onSaved }) {
  const record = snapshot?.data;
  const navigate = useNavigate();
  const { user } = useAuth();
  const { confirm, notify } = useFeedback();
  const queryClient = useQueryClient();
  const action = useWrite();
  const { save, busy, error } = useSave();
  const initial = Object.fromEntries(
    ["ho_ten", "email", "so_dien_thoai", "ngay_sinh", "ngay_vao_lam", "he_so_luong"].map(
      (field) => [field, record?.[field] ?? ""],
    ),
  );
  const [values, setValues] = useState({
    ...initial,
    ten_dang_nhap: "",
    ma_nhan_vien: "",
    mat_khau: "",
    vai_tro_id: "",
  });
  const [roleId, setRoleId] = useState(record?.vai_tro_id || "");
  const lockedAdmin = record?.ma_vai_tro === "quan_tri_vien";
  const editableRoles = roles.filter((role) => role.ma_vai_tro !== "quan_tri_vien");
  const field = (name) => ({
    value: values[name],
    onChange: (event) => setValues({ ...values, [name]: event.target.value }),
  });

  function submit(event) {
    event.preventDefault();
    const profile = Object.fromEntries(
      Object.keys(initial).map((name) => [name, nullable(String(values[name]))]),
    );
    if (record) {
      confirm({
        title: "Xác nhận thay đổi",
        description: "Bạn có chắc chắn muốn thay đổi thông tin tài khoản không?",
        label: "Xác nhận",
        hideImpact: true,
        variant: "profile-save",
        onConfirm: async () => {
          await action.mutateAsync({
            path: `${API.employees}/${record.id}`,
            method: "patch",
            body: profile,
            etag: snapshot?.etag,
            versioned: true,
          });
          notify("Đã lưu thay đổi.");
          onSaved?.();
        },
      });
      return;
    }

    const body = {
      ...profile,
      ten_dang_nhap: values.ten_dang_nhap.trim(),
      ma_nhan_vien: values.ma_nhan_vien.trim(),
      mat_khau: values.mat_khau,
      vai_tro_id: Number(values.vai_tro_id),
    };
    save(
      {
        path: API.employees,
        method: "post",
        body,
        etag: snapshot?.etag,
        versioned: false,
      },
      (result) => navigate(`${base}/${result.data.id}`),
    );
  }

  function changeState() {
    promptAccountStateChange({
      record,
      etag: snapshot?.etag,
      currentUserId: user.id,
      confirm,
      notify,
      queryClient,
    });
  }

  return (
    <div className="stack">
      {record && (
        <div className="actions">
          <strong>
            {record.ma_nhan_vien} · {record.ten_dang_nhap}
          </strong>
          <Badge status={record.trang_thai} />
        </div>
      )}
      <form onSubmit={submit} className="stack">
        <ErrorNotice error={error} />
        {!record && (
          <div className="form-grid">
            <Field
              label="Tên đăng nhập"
              required
              maxLength={255}
              autoComplete="off"
              {...field("ten_dang_nhap")}
            />
            <Field
              label="Mã nhân viên"
              placeholder="NV-000001"
              pattern="NV-[0-9]{6}"
              required
              {...field("ma_nhan_vien")}
            />
            <Field
              label="Mật khẩu ban đầu"
              type="password"
              minLength={8}
              maxLength={1024}
              required
              autoComplete="new-password"
              {...field("mat_khau")}
            />
            <Field as="select" label="Vai trò" required {...field("vai_tro_id")}>
              <option value="">Chọn vai trò</option>
              {editableRoles.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.ten_vai_tro}
                </option>
              ))}
            </Field>
          </div>
        )}
        <div className="form-grid">
          <Field label="Họ tên" {...field("ho_ten")} />
          <Field label="Email" type="email" {...field("email")} />
          <Field label="Số điện thoại" type="tel" {...field("so_dien_thoai")} />
          <Field label="Ngày sinh" type="date" {...field("ngay_sinh")} />
          <Field label="Ngày vào làm" type="date" {...field("ngay_vao_lam")} />
          <Field
            label="Hệ số lương"
            type="number"
            min="0"
            max="999.99"
            step="0.01"
            {...field("he_so_luong")}
          />
        </div>
        <div className="actions actions-end">
          {onCancel ? (
            <Button variant="secondary" onClick={onCancel}>
              Hủy
            </Button>
          ) : (
            <Link to={base}>Hủy</Link>
          )}
          <Button type="submit" disabled={busy}>
            {busy ? "Đang lưu…" : record ? "Lưu hồ sơ" : "Tạo tài khoản"}
          </Button>
        </div>
      </form>
      {record && (
        <>
          <section className="form-section stack">
            <h3>Phân quyền</h3>
            <Field
              as="select"
              label="Vai trò"
              disabled={lockedAdmin}
              value={roleId}
              onChange={(event) => setRoleId(event.target.value)}
            >
              {roles
                .filter((role) => role.ma_vai_tro !== "quan_tri_vien" || lockedAdmin)
                .map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.ten_vai_tro}
                  </option>
                ))}
            </Field>
            <Button
              variant="secondary"
              disabled={lockedAdmin || Number(roleId) === record.vai_tro_id}
              onClick={() =>
                confirm({
                  title: "Đổi vai trò nhân viên",
                  description: `Đổi vai trò cho ${record.ma_nhan_vien}. Quyền có hiệu lực ở request tiếp theo.`,
                  onConfirm: async () => {
                    await action.mutateAsync({
                      path: `${API.employees}/${record.id}/vai_tro`,
                      method: "put",
                      body: { vai_tro_id: Number(roleId) },
                      etag: snapshot.etag,
                    });
                    notify("Đã cập nhật vai trò.");
                  },
                })
              }
            >
              Cập nhật vai trò
            </Button>
            {lockedAdmin && (
              <Notice>Tài khoản quản trị viên duy nhất không thể bị hạ quyền hoặc khóa.</Notice>
            )}
          </section>
          <section className="form-section stack">
            <h3>Trạng thái tài khoản</h3>
            <div className="actions">
              <Button
                variant="secondary"
                disabled={lockedAdmin || record.id === user.id}
                onClick={changeState}
              >
                {record.trang_thai === "bi_khoa" ? "Mở khóa tài khoản…" : "Khóa tài khoản…"}
              </Button>
              <Button variant="secondary" reason="Chưa có API đặt lại mật khẩu nhân viên.">
                Đặt lại mật khẩu…
              </Button>
            </div>
            <small className="muted">
              Khóa thay cho xóa vĩnh viễn; giữ nguyên mọi tham chiếu lịch sử.
            </small>
          </section>
        </>
      )}
    </div>
  );
}
