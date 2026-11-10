import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  Ban,
  Calendar,
  CirclePercent,
  Eye,
  EyeOff,
  Info,
  KeyRound,
  Layers,
  LockOpen,
  Mail,
  Pencil,
  Phone,
  Plus,
  Save,
  Search,
  UserRound,
  X,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { API } from "../../lib/api/endpoints.js";
import { ApiError } from "../../lib/api/contract.js";
import { readResource, writeResource } from "../../lib/api/client.js";
import { useChoices, useCollection, useDetail } from "../../lib/api/useResources.js";
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
import { AdminRoleBadge, AdminStatusBadge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import { ErrorNotice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";

const base = "/admin/tai-khoan";
const PROFILE_FIELDS = [
  "ho_ten",
  "email",
  "so_dien_thoai",
  "ngay_sinh",
  "ngay_vao_lam",
  "he_so_luong",
];

function extractProfileDraft(record) {
  return Object.fromEntries(PROFILE_FIELDS.map((field) => [field, record?.[field] ?? ""]));
}

function normalizeProfileField(field, value) {
  const normalized = nullable(String(value ?? ""));
  if (field === "he_so_luong" && normalized !== null) {
    const num = Number(normalized);
    return Number.isNaN(num) ? normalized : num;
  }
  return normalized;
}

function isProfileChanged(record, values) {
  return PROFILE_FIELDS.some((field) => {
    const left = normalizeProfileField(field, record?.[field]);
    const right = normalizeProfileField(field, values[field]);
    return left !== right;
  });
}

function promptAccountStateChange({ record, etag, currentUserId, confirm, notify, queryClient, onError }) {
  if (!record) return;
  if (record.ma_vai_tro === "quan_tri_vien" || record.id === currentUserId) {
    return;
  }
  if (!etag) {
    onError?.(
      new ApiError("Chưa tải được phiên bản dữ liệu để xác nhận. Vui lòng tải lại.", {
        status: 428,
        code: "PRECONDITION_REQUIRED",
      }),
    );
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
  const { user, login, logout } = useAuth();
  const { confirm, notify, showSuccess } = useFeedback();
  const queryClient = useQueryClient();
  const detail = useDetail(API.employees, id);
  const snapshot = detail.data;
  const record = snapshot?.data;

  const currentIdRef = useRef(id);
  const editBaselineRef = useRef(null);
  const editInitializedRef = useRef(false);

  if (currentIdRef.current !== id) {
    currentIdRef.current = id;
    editBaselineRef.current = null;
    editInitializedRef.current = false;
  }

  if (!isEditing) {
    editBaselineRef.current = snapshot;
  } else if (!editBaselineRef.current && snapshot) {
    editBaselineRef.current = snapshot;
  }

  const activeBaselineRecord = editBaselineRef.current?.data || record;
  const lockedAdmin = activeBaselineRecord?.ma_vai_tro === "quan_tri_vien";
  const canChangeState = activeBaselineRecord && !lockedAdmin && activeBaselineRecord.id !== user.id;
  const isLocked = activeBaselineRecord?.trang_thai === "bi_khoa";

  const [values, setValues] = useState(() => extractProfileDraft(activeBaselineRecord));
  const [roleId, setRoleId] = useState(() => String(activeBaselineRecord?.vai_tro_id ?? ""));
  const [newPassword, setNewPassword] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => {
    if (!activeBaselineRecord) return;
    if (!isEditing) {
      editInitializedRef.current = false;
      setNewPassword("");
      setPasswordVisible(false);
      setValues(extractProfileDraft(activeBaselineRecord));
      setRoleId(String(activeBaselineRecord.vai_tro_id ?? ""));
      setSaveError(null);
      return;
    }
    if (!editInitializedRef.current) {
      editInitializedRef.current = true;
      setNewPassword("");
      setPasswordVisible(false);
      setValues(extractProfileDraft(activeBaselineRecord));
      setRoleId(String(activeBaselineRecord.vai_tro_id ?? ""));
      setSaveError(null);
    }
  }, [isEditing, activeBaselineRecord, id]);

  function handleStartEdit() {
    setNewPassword("");
    setPasswordVisible(false);
    const base = editBaselineRef.current?.data || record;
    if (base) {
      setValues(extractProfileDraft(base));
      setRoleId(String(base.vai_tro_id ?? ""));
    }
    setSaveError(null);
    editInitializedRef.current = true;
    onStartEdit();
  }

  function handleCancelEdit() {
    setNewPassword("");
    setPasswordVisible(false);
    const base = editBaselineRef.current?.data || record;
    if (base) {
      setValues(extractProfileDraft(base));
      setRoleId(String(base.vai_tro_id ?? ""));
    }
    setSaveError(null);
    editInitializedRef.current = false;
    onCancelEdit();
  }

  function handleToggleState() {
    const target = editBaselineRef.current?.data || record;
    if (!target) return;
    promptAccountStateChange({
      record: target,
      etag: editBaselineRef.current?.etag || snapshot?.etag,
      currentUserId: user.id,
      confirm,
      notify,
      queryClient,
      onError: setSaveError,
    });
  }

  function updateField(name) {
    return (event) => {
      setValues((previous) => ({ ...previous, [name]: event.target.value }));
    };
  }

  function handleInlineSubmit(event) {
    event.preventDefault();
    const baseSnapshot = editBaselineRef.current || snapshot;
    const baseRecord = baseSnapshot?.data;
    if (!baseRecord || busy) return;

    const profileDirty = isProfileChanged(baseRecord, values);
    const passwordDirty = newPassword.length > 0;
    if (passwordDirty && newPassword.length < 8) {
      setSaveError(new ApiError("Mật khẩu mới phải có từ 8 đến 1024 ký tự.", {
        status: 422,
        code: "VALIDATION_ERROR",
      }));
      return;
    }
    const parsedRoleId = Number(roleId);
    const roleDirty =
      !lockedAdmin &&
      Boolean(roleId) &&
      !Number.isNaN(parsedRoleId) &&
      parsedRoleId !== Number(baseRecord.vai_tro_id);

    if (!profileDirty && !roleDirty && !passwordDirty) {
      setSaveError(null);
      editInitializedRef.current = false;
      onCancelEdit();
      return;
    }

    const submission = {
      id: baseRecord.id,
      reviewedEtag: baseSnapshot.etag,
      baselineRecord: baseRecord,
      values: { ...values },
      targetRoleId: parsedRoleId,
      needProfileWrite: profileDirty,
      needRoleWrite: roleDirty,
      needPasswordWrite: passwordDirty,
      newPassword,
      savedSteps: [],
    };

    confirm({
      title: "Xác nhận thay đổi",
      description: "Bạn có chắc chắn muốn thay đổi thông tin tài khoản không?",
      label: "Xác nhận",
      hideImpact: true,
      variant: "profile-save",
      onConfirm: async () => {
        if (busy) return;
        if (!submission.reviewedEtag) {
          const missingEtagError = new ApiError(
            "Chưa tải được phiên bản dữ liệu để xác nhận. Vui lòng tải lại.",
            { status: 428, code: "PRECONDITION_REQUIRED" },
          );
          setSaveError(missingEtagError);
          throw missingEtagError;
        }

        setBusy(true);
        setSaveError(null);
        let failedStep = "cập nhật hồ sơ";
        let workingRecord = submission.baselineRecord;
        let currentEtag = submission.reviewedEtag;

        const profilePayload = Object.fromEntries(
          PROFILE_FIELDS.map((name) => [name, nullable(String(submission.values[name] ?? ""))]),
        );

        const updateCache = (nextSnap) => {
          editBaselineRef.current = nextSnap;
          const detailKey = [
            "resources",
            user?.id,
            user?.ma_vai_tro,
            `${API.employees}/${id}`,
            {},
          ];
          queryClient.setQueryData(detailKey, nextSnap);
        };

        try {
          if (submission.needProfileWrite) {
            const profileRes = await writeResource({
              path: `${API.employees}/${submission.id}`,
              method: "patch",
              body: profilePayload,
              etag: currentEtag,
            });
            submission.savedSteps.push("thông tin hồ sơ");
            workingRecord = {
              ...workingRecord,
              ...(profileRes?.data || profilePayload),
            };
            currentEtag = profileRes?.etag;
            const nextSnap = {
              data: workingRecord,
              meta: profileRes?.meta || baseSnapshot?.meta,
              etag: currentEtag,
            };
            updateCache(nextSnap);
            submission.needProfileWrite = false;
            submission.reviewedEtag = currentEtag;
            submission.baselineRecord = workingRecord;
          }

          if (submission.needRoleWrite) {
            failedStep = "cập nhật vai trò";
            if (!currentEtag) {
              throw new ApiError(
                "Phản hồi lưu hồ sơ không trả về ETag mới để tiếp tục cập nhật vai trò.",
                { status: 428, code: "PRECONDITION_REQUIRED" },
              );
            }
            const roleRes = await writeResource({
              path: `${API.employees}/${submission.id}/vai_tro`,
              method: "put",
              body: { vai_tro_id: submission.targetRoleId },
              etag: currentEtag,
            });
            const matchedRole = (roles.data || []).find(
              (item) => Number(item.id) === submission.targetRoleId,
            );
            workingRecord = {
              ...workingRecord,
              ...(roleRes?.data || {}),
              vai_tro_id: submission.targetRoleId,
              ma_vai_tro:
                roleRes?.data?.ma_vai_tro ||
                matchedRole?.ma_vai_tro ||
                workingRecord.ma_vai_tro,
            };
            currentEtag = roleRes?.etag || currentEtag;
            const nextSnap = {
              data: workingRecord,
              meta: roleRes?.meta || baseSnapshot?.meta,
              etag: currentEtag,
            };
            updateCache(nextSnap);
            submission.savedSteps.push("vai trò");
            submission.needRoleWrite = false;
            submission.reviewedEtag = currentEtag;
            submission.baselineRecord = workingRecord;
          }

          if (submission.needPasswordWrite) {
            failedStep = "đặt lại mật khẩu";
            const passwordRes = await writeResource({
              path: `${API.employees}/${submission.id}/dat_lai_mat_khau`,
              method: "post",
              body: { mat_khau_moi: submission.newPassword },
              etag: currentEtag,
            });
            // Renew our own token before any cache update can trigger a refetch.
            if (submission.id === user.id) {
              try {
                await login({
                  ten_dang_nhap: user.ten_dang_nhap,
                  mat_khau: submission.newPassword,
                });
              } catch {
                submission.newPassword = "";
                setNewPassword("");
                setPasswordVisible(false);
                logout("Đã đặt lại mật khẩu. Vui lòng đăng nhập lại.");
                return;
              }
            }
            workingRecord = { ...workingRecord, ...(passwordRes?.data || {}) };
            currentEtag = passwordRes?.etag || currentEtag;
            updateCache({
              data: workingRecord,
              meta: passwordRes?.meta || baseSnapshot?.meta,
              etag: currentEtag,
            });
            submission.needPasswordWrite = false;
            submission.newPassword = "";
            submission.reviewedEtag = currentEtag;
            submission.baselineRecord = workingRecord;
            submission.savedSteps.push("mật khẩu");
            setNewPassword("");
            setPasswordVisible(false);
          }

          failedStep = "tải lại dữ liệu";
          await queryClient.invalidateQueries({
            queryKey: ["resources"],
          });
          editInitializedRef.current = false;
          onCancelEdit();
          showSuccess({ title: "Lưu thành công" });
        } catch (failure) {
          if (submission.savedSteps.length) {
            await queryClient.invalidateQueries({
              queryKey: ["resources", user?.id, user?.ma_vai_tro, API.employees],
            });
            const partialError = new ApiError(
              `Đã lưu ${submission.savedSteps.join(" và ")}, nhưng ${failedStep} thất bại: ${
                failure?.message || "Không thể lưu thay đổi."
              }`,
              {
                status: failure?.status || 500,
                code: failure?.code || "PARTIAL_SAVE_FAILED",
                details: failure?.details || [],
                requestId: failure?.requestId,
                ticketId: failure?.ticketId,
                uncertain: Boolean(failure?.uncertain),
              },
            );
            setSaveError(partialError);
            throw partialError;
          }
          setSaveError(failure);
          throw failure;
        } finally {
          setBusy(false);
        }
      },
    });
  }

  const roleChoices = (roles.data || []).filter(
    (role) => role.ma_vai_tro !== "quan_tri_vien" || lockedAdmin,
  );

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
        {activeBaselineRecord && (
          <div className="admin-detail-actions">
            {isEditing ? (
              <>
                <button
                  type="button"
                  className="admin-subbar-btn"
                  onClick={handleCancelEdit}
                  disabled={busy}
                >
                  <X size={15} aria-hidden="true" />
                  <span>Hủy</span>
                </button>
                <button
                  type="submit"
                  form="account-inline-edit-form"
                  className="btn btn-primary admin-primary-cta"
                  disabled={busy}
                >
                  <Save size={15} aria-hidden="true" />
                  <span>{busy ? "Đang lưu…" : "Lưu"}</span>
                </button>
              </>
            ) : (
              <button
                type="button"
                className="btn btn-primary admin-primary-cta"
                onClick={handleStartEdit}
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
              disabled={!canChangeState || busy}
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
        {activeBaselineRecord && (
          <div className="admin-detail-grid" key={id}>
            <section className="admin-surface admin-identity-card">
              <div className="admin-identity-avatar" aria-hidden="true">
                {initials(activeBaselineRecord.ho_ten || activeBaselineRecord.ten_dang_nhap)}
              </div>
              <h2 className="admin-identity-name">{activeBaselineRecord.ho_ten || "Chưa có họ tên"}</h2>
              <p className="admin-identity-code">{activeBaselineRecord.ma_nhan_vien}</p>
              <hr className="admin-identity-divider" />
              <div className="admin-identity-badges">
                <AdminRoleBadge role={activeBaselineRecord.ma_vai_tro} />
                <AdminStatusBadge status={activeBaselineRecord.trang_thai} />
              </div>
            </section>

            <section className="admin-surface admin-info-card">
              <div className="admin-card-title">
                <Info size={18} className="admin-title-icon" aria-hidden="true" />
                <h2>Thông tin tài khoản</h2>
              </div>

              <ErrorNotice error={saveError} />

              {isEditing ? (
                <form id="account-inline-edit-form" onSubmit={handleInlineSubmit}>
                  <dl className="admin-detail-rows is-editing">
                    <InlineEditRow icon={UserRound} label="Họ tên" htmlFor="inline-ho-ten">
                      <input
                        id="inline-ho-ten"
                        className="admin-inline-input"
                        type="text"
                        value={values.ho_ten}
                        onChange={updateField("ho_ten")}
                        disabled={busy}
                      />
                    </InlineEditRow>
                    <InlineEditRow icon={Calendar} label="Ngày sinh" htmlFor="inline-ngay-sinh">
                      <input
                        id="inline-ngay-sinh"
                        className="admin-inline-input"
                        type="date"
                        value={values.ngay_sinh}
                        onChange={updateField("ngay_sinh")}
                        disabled={busy}
                      />
                    </InlineEditRow>
                    <InlineEditRow
                      icon={Phone}
                      label="Số điện thoại"
                      htmlFor="inline-so-dien-thoai"
                    >
                      <input
                        id="inline-so-dien-thoai"
                        className="admin-inline-input"
                        type="tel"
                        value={values.so_dien_thoai}
                        onChange={updateField("so_dien_thoai")}
                        disabled={busy}
                      />
                    </InlineEditRow>
                    <InlineEditRow icon={Mail} label="Email" htmlFor="inline-email">
                      <input
                        id="inline-email"
                        className="admin-inline-input"
                        type="email"
                        value={values.email}
                        onChange={updateField("email")}
                        disabled={busy}
                      />
                    </InlineEditRow>
                    <DetailRow
                      icon={UserRound}
                      label="Tên đăng nhập"
                      value={activeBaselineRecord.ten_dang_nhap || "—"}
                      readOnly
                    />
                    <InlineEditRow icon={KeyRound} label="Mật khẩu" htmlFor="inline-mat-khau">
                      <div className="admin-inline-password">
                        <input
                          id="inline-mat-khau"
                          className="admin-inline-input"
                          type={passwordVisible ? "text" : "password"}
                          autoComplete="new-password"
                          placeholder="Để trống nếu không đổi"
                          maxLength={1024}
                          value={newPassword}
                          onChange={(event) => setNewPassword(event.target.value)}
                          disabled={busy}
                        />
                        <button
                          type="button"
                          className="admin-inline-password-toggle"
                          aria-label={passwordVisible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                          aria-pressed={passwordVisible}
                          onClick={() => setPasswordVisible(!passwordVisible)}
                          disabled={busy}
                        >
                          {passwordVisible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
                        </button>
                      </div>
                    </InlineEditRow>
                    <InlineEditRow icon={Layers} label="Vai trò" htmlFor="inline-vai-tro">
                      <select
                        id="inline-vai-tro"
                        className="admin-inline-select"
                        value={roleId}
                        onChange={(event) => setRoleId(event.target.value)}
                        disabled={lockedAdmin || busy || roles.isLoading}
                      >
                        {roleChoices.length ? (
                          roleChoices.map((role) => (
                            <option key={role.id} value={role.id}>
                              {ROLE_LABELS[role.ma_vai_tro] || role.ten_vai_tro}
                            </option>
                          ))
                        ) : (
                          <option value={activeBaselineRecord.vai_tro_id ?? ""}>
                            {ROLE_LABELS[activeBaselineRecord.ma_vai_tro] || activeBaselineRecord.ma_vai_tro || "—"}
                          </option>
                        )}
                      </select>
                    </InlineEditRow>
                    <InlineEditRow
                      icon={Calendar}
                      label="Ngày vào làm"
                      htmlFor="inline-ngay-vao-lam"
                    >
                      <input
                        id="inline-ngay-vao-lam"
                        className="admin-inline-input"
                        type="date"
                        value={values.ngay_vao_lam}
                        onChange={updateField("ngay_vao_lam")}
                        disabled={busy}
                      />
                    </InlineEditRow>
                    <InlineEditRow
                      icon={CirclePercent}
                      label="Hệ số lương"
                      htmlFor="inline-he-so-luong"
                    >
                      <input
                        id="inline-he-so-luong"
                        className="admin-inline-input"
                        type="number"
                        min="0"
                        max="999.99"
                        step="0.01"
                        value={values.he_so_luong}
                        onChange={updateField("he_so_luong")}
                        disabled={busy}
                      />
                    </InlineEditRow>
                    <DetailRow
                      icon={Activity}
                      label="Trạng thái"
                      value={<AdminStatusBadge status={activeBaselineRecord.trang_thai} />}
                      plain
                    />
                  </dl>
                </form>
              ) : (
                <dl className="admin-detail-rows">
                  <DetailRow icon={UserRound} label="Họ tên" value={activeBaselineRecord.ho_ten || "—"} />
                  <DetailRow
                    icon={Calendar}
                    label="Ngày sinh"
                    value={formatDate(activeBaselineRecord.ngay_sinh)}
                  />
                  <DetailRow
                    icon={Phone}
                    label="Số điện thoại"
                    value={activeBaselineRecord.so_dien_thoai || "—"}
                  />
                  <DetailRow icon={Mail} label="Email" value={activeBaselineRecord.email || "—"} />
                  <DetailRow
                    icon={UserRound}
                    label="Tên đăng nhập"
                    value={activeBaselineRecord.ten_dang_nhap || "—"}
                  />
                  <DetailRow icon={KeyRound} label="Mật khẩu" value="••••••••" />
                  <DetailRow
                    icon={Layers}
                    label="Vai trò"
                    value={ROLE_LABELS[activeBaselineRecord.ma_vai_tro] || activeBaselineRecord.ma_vai_tro || "—"}
                  />
                  <DetailRow
                    icon={Calendar}
                    label="Ngày vào làm"
                    value={formatDate(activeBaselineRecord.ngay_vao_lam)}
                  />
                  <DetailRow
                    icon={CirclePercent}
                    label="Hệ số lương"
                    value={formatCoefficient(activeBaselineRecord.he_so_luong)}
                  />
                  <DetailRow
                    icon={Activity}
                    label="Trạng thái"
                    value={<AdminStatusBadge status={activeBaselineRecord.trang_thai} />}
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

function DetailRow({ icon, label, value, plain = false, readOnly = false }) {
  const IconComponent = icon;
  const ddClass = [plain ? "is-plain" : "", readOnly ? "is-readonly" : ""]
    .filter(Boolean)
    .join(" ");
  return (
    <div className="admin-detail-row">
      <dt>
        <IconComponent size={18} aria-hidden="true" />
        <span>{label}</span>
      </dt>
      <dd className={ddClass}>{value}</dd>
    </div>
  );
}

function InlineEditRow({ icon, label, htmlFor, children }) {
  const IconComponent = icon;
  return (
    <div className="admin-detail-row is-editable">
      <dt>
        <IconComponent size={18} aria-hidden="true" />
        <label htmlFor={htmlFor}>{label}</label>
      </dt>
      <dd className="is-input">{children}</dd>
    </div>
  );
}

function EmployeeForm({ snapshot, roles }) {
  const navigate = useNavigate();
  const { save, busy, error } = useSave();
  const [values, setValues] = useState({
    ho_ten: "",
    email: "",
    so_dien_thoai: "",
    ngay_sinh: "",
    ngay_vao_lam: "",
    he_so_luong: "",
    ten_dang_nhap: "",
    ma_nhan_vien: "",
    mat_khau: "",
    vai_tro_id: "",
  });
  const editableRoles = roles.filter((role) => role.ma_vai_tro !== "quan_tri_vien");
  const field = (name) => ({
    value: values[name],
    onChange: (event) => setValues({ ...values, [name]: event.target.value }),
  });

  function submit(event) {
    event.preventDefault();
    const profile = Object.fromEntries(
      PROFILE_FIELDS.map((name) => [name, nullable(String(values[name]))]),
    );
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

  return (
    <div className="stack">
      <form onSubmit={submit} className="stack">
        <ErrorNotice error={error} />
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
          <Link to={base}>Hủy</Link>
          <Button type="submit" disabled={busy}>
            {busy ? "Đang lưu…" : "Tạo tài khoản"}
          </Button>
        </div>
      </form>
    </div>
  );
}
