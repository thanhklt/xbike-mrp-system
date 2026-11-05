import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useChoices, useCollection, useDetail, useWrite } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { ROLE_LABELS, nullable } from "../../lib/format.js";
import { useAuth } from "./AuthProvider.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel } from "../../components/RecordPanel.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import { ErrorNotice, QueryState, Notice } from "../../components/QueryState.jsx";
import { statusFilter } from "../../components/ResourceFields.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
const base = "/admin/tai-khoan";
export function UsersPage() {
  const { id } = useParams();
  const collection = useCollection(API.employees, { sort: "id" });
  const detail = useDetail(API.employees, id);
  const roles = useChoices(API.roles);
  return (
    <>
      <PageHeader
        title="Tài khoản"
        subtitle="Quản lý hồ sơ, phân quyền và trạng thái tài khoản nhân viên."
        action={
          <Link className="btn btn-primary" to={`${base}/moi`}>
            Tạo tài khoản
          </Link>
        }
      />
      <div>
        <Collection
          collection={collection}
          filters={[
            {
              name: "vai_tro_id",
              label: "Vai trò",
              as: "select",
              options: [
                { value: "", label: "Tất cả" },
                ...(roles.data || []).map((role) => ({
                  value: role.id,
                  label: ROLE_LABELS[role.ma_vai_tro],
                })),
              ],
            },
            statusFilter(["hoat_dong", "bi_khoa"]),
            {
              name: "sort",
              label: "Sắp xếp",
              as: "select",
              options: [
                { value: "id", label: "ID tăng dần" },
                { value: "ma_nhan_vien", label: "Mã nhân viên" },
                { value: "ho_ten", label: "Họ tên" },
                { value: "ten_dang_nhap", label: "Tên đăng nhập" },
              ],
            },
          ]}
          columns={[
            {
              key: "ma_nhan_vien",
              label: "Mã NV",
              render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_nhan_vien}</Link>,
            },
            {
              key: "ho_ten",
              label: "Họ tên · tài khoản",
              render: (row) => (
                <>
                  <strong>{row.ho_ten || "Chưa có họ tên"}</strong>
                  <small>{row.ten_dang_nhap}</small>
                </>
              ),
            },
            { key: "ma_vai_tro", label: "Vai trò", render: (row) => ROLE_LABELS[row.ma_vai_tro] },
            {
              key: "email",
              label: "Liên hệ",
              render: (row) => (
                <>
                  {row.email || "—"}
                  <small>{row.so_dien_thoai}</small>
                </>
              ),
            },
            {
              key: "trang_thai",
              label: "Trạng thái",
              render: (row) => <Badge status={row.trang_thai} />,
            },
            {
              key: "action",
              label: "Thao tác",
              render: (row) => <Link to={`${base}/${row.id}`}>Sửa →</Link>,
            },
          ]}
        />
        <RecordPanel
          id={id}
          query={detail}
          base={base}
          title={id === "moi" ? "Tạo tài khoản" : "Hồ sơ tài khoản"}
        >
          {(snapshot) => (
            <QueryState query={roles}>
              <EmployeeForm snapshot={snapshot} roles={roles.data || []} />
            </QueryState>
          )}
        </RecordPanel>
      </div>
    </>
  );
}
function EmployeeForm({ snapshot, roles }) {
  const record = snapshot?.data;
  const navigate = useNavigate();
  const { user } = useAuth();
  const { confirm, notify } = useFeedback();
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
    const body = record
      ? profile
      : {
          ...profile,
          ten_dang_nhap: values.ten_dang_nhap.trim(),
          ma_nhan_vien: values.ma_nhan_vien.trim(),
          mat_khau: values.mat_khau,
          vai_tro_id: Number(values.vai_tro_id),
        };
    save(
      {
        path: record ? `${API.employees}/${record.id}` : API.employees,
        method: record ? "patch" : "post",
        body,
        etag: snapshot?.etag,
        versioned: Boolean(record),
      },
      (result) => navigate(`${base}/${result.data.id}`),
    );
  }
  function changeState() {
    const unlock = record.trang_thai === "bi_khoa";
    confirm({
      title: unlock ? "Mở khóa tài khoản" : "Khóa tài khoản",
      description: `${record.ma_nhan_vien} · ${record.ho_ten || record.ten_dang_nhap}`,
      reason: true,
      danger: !unlock,
      impact:
        "Bảo toàn hồ sơ, công việc và chứng từ đã lập. Khóa tài khoản chặn mọi request tiếp theo.",
      onConfirm: async (reason) => {
        await action.mutateAsync({
          path: `${API.employees}/${record.id}${unlock ? "/mo_khoa" : ""}`,
          method: unlock ? "post" : "delete",
          body: { ly_do: reason },
          etag: snapshot.etag,
        });
        notify(unlock ? "Đã mở khóa tài khoản." : "Đã khóa tài khoản.");
      },
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
          <Link to={base}>Hủy</Link>
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
