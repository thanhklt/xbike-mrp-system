import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import {
  useCatalog,
  useChoices,
  useCollection,
  useDetail,
  useWrite,
} from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { itemName, formatDate } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Field } from "../../components/Field.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import {
  ItemSelect,
  EmployeeSelect,
} from "../../components/ResourceFields.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
import {
  REQUEST_TYPES,
  REQUEST_TYPE_LABELS,
  initialRequestValues,
  canEditRequest,
  canCancelRequest,
  requestDetailEntries,
  requestListFilters,
  requestCreateBody,
  sendConfirmEntries,
} from "./requestForm.js";

// UC-25 Xem danh sách yêu cầu sản xuất — Main 1–4; A1, A3 (specs/use_cases/production/UC-25.md)
export function RequestsPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const manager = user.ma_vai_tro === "quan_ly";
  const base = manager ? "/kho/yeu-cau" : "/nv/yeu-cau";
  const collection = useCollection(API.requests, {});
  const detail = useDetail(API.requests, id);
  const catalog = useCatalog();
  const employees = useChoices(API.employees, {}, manager);
  const items = catalog.data?.data || [];
  return (
    <>
      <PageHeader
        title={manager ? "Yêu cầu sản xuất" : "Yêu cầu được giao"}
        subtitle={manager
          ? "Lập yêu cầu sản xuất và gửi cho nhân viên được giao."
          : "Yêu cầu sản xuất được giao cho bạn, từ khi đã gửi."}
        action={
          manager && (
            <Link className="btn btn-primary" to={`${base}/moi`}>
              Tạo yêu cầu sản xuất
            </Link>
          )
        }
      />
      <Collection
        collection={collection}
        filters={requestListFilters(manager)}
        columns={[
          {
            key: "ma_yeu_cau_san_xuat",
            label: "Mã yêu cầu",
            render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_yeu_cau_san_xuat}</Link>,
          },
          {
            key: "mat_hang_id",
            label: "Thành phẩm",
            render: (row) => itemName(items, row.mat_hang_id),
          },
          {
            key: "loai_yeu_cau",
            label: "Loại yêu cầu",
            render: (row) => REQUEST_TYPE_LABELS[row.loai_yeu_cau],
          },
          {
            key: "han_hoan_thanh",
            label: "Hạn hoàn thành",
            render: (row) => formatDate(row.han_hoan_thanh),
          },
          { key: "so_luong", label: "Số lượng cần", numeric: true },
          {
            key: "trang_thai",
            label: "Trạng thái",
            render: (row) => <Badge status={row.trang_thai} />,
          },
          {
            key: "action",
            label: "Thao tác",
            render: (row) => <Link to={`${base}/${row.id}`}>Mở →</Link>,
          },
        ]}
      />
      <RecordPanel
        id={id}
        query={detail}
        base={base}
        title={id === "moi" ? "Tạo yêu cầu sản xuất" : "Chi tiết yêu cầu"}
      >
        {(snapshot) => (
          <QueryState query={catalog}>
            <RequestEditor
              snapshot={snapshot}
              items={items}
              employees={employees}
              manager={manager}
              base={base}
            />
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}
function RequestEditor({ snapshot, items, employees, manager, base }) {
  const record = snapshot?.data;
  const initial = initialRequestValues(record);
  const [values, setValues] = useState(initial);
  const [editing, setEditing] = useState(false);
  const mutation = useWrite();
  const { save, busy, error } = useSave();
  const { confirm, notify } = useFeedback();
  const navigate = useNavigate();
  const editable = canEditRequest(record, manager);
  const showForm = manager && (!record || (editable && editing));
  const field = (name) => ({
    value: values[name],
    onChange: (event) => {
      setValues({ ...values, [name]: event.target.value });
    },
  });
  // UC-23 Lập và gửi yêu cầu sản xuất — Main 4–6; A1, A2 (specs/use_cases/production/UC-23.md)
  // UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — A1 lưu đủ thông tin, về chế độ xem (specs/use_cases/production/UC-24.md)
  function submit(event) {
    event.preventDefault();
    save(
      {
        path: record ? `${API.requests}/${record.id}` : API.requests,
        method: record ? "patch" : "post",
        body: requestCreateBody(values),
        etag: snapshot?.etag,
        versioned: Boolean(record),
      },
      (result) => {
        if (record) setEditing(false);
        navigate(`${base}/${result.data.id}`);
        if (!record) send(result.data, result.etag);
      },
    );
  }
  // UC-23 Lập và gửi yêu cầu sản xuất — Main 6–9; A2, A3 (specs/use_cases/production/UC-23.md)
  function send(request, etag) {
    confirm({
      title: "Gửi yêu cầu sản xuất",
      description: request.ma_yeu_cau_san_xuat,
      content: <InfoGrid entries={sendConfirmEntries(request, items, employees.data || [])} />,
      impact: "Chưa thay đổi tồn kho và phần đang giữ.",
      onConfirm: async () => {
        await mutation.mutateAsync({
          path: `${API.requests}/${request.id}/gui`,
          body: {},
          etag,
        });
        notify("Đã gửi yêu cầu cho nhân viên.");
      },
    });
  }
  // UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — A2 xác nhận xóa và về danh sách (specs/use_cases/production/UC-24.md)
  function cancel(remove = false) {
    confirm({
      title: remove ? "Xóa yêu cầu nháp" : "Hủy yêu cầu sản xuất",
      description: record.ma_yeu_cau_san_xuat,
      reason: !remove,
      danger: true,
      onConfirm: async (reason) => {
        await mutation.mutateAsync({
          path: `${API.requests}/${record.id}${remove ? "" : "/huy"}`,
          method: remove ? "delete" : "post",
          body: remove ? {} : { ly_do: reason },
          etag: snapshot.etag,
        });
        notify("Đã xử lý yêu cầu.");
        if (remove) navigate(base);
      },
    });
  }
  // UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — A1 mở form điền sẵn (specs/use_cases/production/UC-24.md)
  function edit() {
    setValues(initialRequestValues(record));
    setEditing(true);
  }
  // UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — A1 bỏ sửa, khôi phục giá trị và chế độ xem (specs/use_cases/production/UC-24.md)
  function discardEdit() {
    setValues(initialRequestValues(record));
    setEditing(false);
  }
  if (!record && !manager) return <Notice>Bạn chỉ có thể xem yêu cầu được giao.</Notice>;
  const submitButton = (
    <Button type="submit" disabled={busy}>
      {record ? "Lưu nháp" : "Tạo"}
    </Button>
  );
  return (
    <div className="stack">
      {record && (
        <>
          <div className="actions">
            <h3>{record.ma_yeu_cau_san_xuat}</h3>
            <Badge status={record.trang_thai} />
          </div>
          <InfoGrid entries={requestDetailEntries(record, items, employees.data || [])} />
        </>
      )}
      <ErrorNotice error={(showForm && error) || mutation.error} />
      {showForm && (
        <QueryState query={employees}>
          <form className="stack" onSubmit={submit}>
            <div className="form-grid">
              <Field as="select" label="Loại yêu cầu" required {...field("loai_yeu_cau")}>
                {REQUEST_TYPES.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Field>
              <ItemSelect
                label="Thành phẩm"
                required
                items={items}
                types={["thanh_pham"]}
                {...field("mat_hang_id")}
              />
              <Field
                label="Số lượng cần"
                type="number"
                required
                min="1"
                step="1"
                max="2147483647"
                {...field("so_luong")}
              />
              <Field label="Hạn hoàn thành" type="date" required {...field("han_hoan_thanh")} />
            </div>
            <EmployeeSelect
              employees={employees.data}
              required
              label="Nhân viên được giao"
              {...field("nhan_vien_duoc_giao_id")}
            />
            {record ? (
              <div className="actions actions-end">
                <Button type="button" variant="secondary" onClick={discardEdit} disabled={busy}>
                  Bỏ sửa
                </Button>
                {submitButton}
              </div>
            ) : (
              submitButton
            )}
          </form>
        </QueryState>
      )}
      {editable && !editing && (
        <div className="actions actions-end">
          <Button variant="secondary" onClick={edit}>
            Sửa
          </Button>
          <Button variant="secondary" onClick={() => cancel(true)}>
            Xóa nháp
          </Button>
          <Button disabled={mutation.isPending} onClick={() => send(record, snapshot.etag)}>
            Gửi yêu cầu cho nhân viên
          </Button>
        </div>
      )}
      {canCancelRequest(record, manager) && (
        <div className="actions">
          <Button variant="secondary" onClick={() => cancel()}>
            Hủy yêu cầu…
          </Button>
          {!["nhap", "cho_bo_sung_linh_kien"].includes(record.trang_thai) && (
            <Link
              className="btn btn-secondary"
              to={`/kho/phieu-xuat/moi?loai_phieu=xuat_thanh_pham&yeu_cau_san_xuat_id=${record.id}`}
            >
              Tạo phiếu xuất thành phẩm
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
