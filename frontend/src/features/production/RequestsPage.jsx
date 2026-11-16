import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { readResource } from "../../lib/api/client.js";
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
import { DataTable } from "../../components/DataTable.jsx";
import {
  ItemSelect,
  EmployeeSelect,
} from "../../components/ResourceFields.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
import {
  REQUEST_TYPES,
  CHECK_COLUMNS,
  canCheckRequest,
  checkConfirmEntries,
  checkLines,
  checkImpact,
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
  // RecordPanel remounts the editor when ETag changes after confirmation.
  const [checkResult, setCheckResult] = useState(null);
  useEffect(() => setCheckResult(null), [id]);
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
              userId={user.id}
              checkResult={checkResult}
              onCheckResult={setCheckResult}
            />
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}
function RequestEditor({ snapshot, items, employees, manager, base, userId, checkResult, onCheckResult }) {
  const record = snapshot?.data;
  const initial = initialRequestValues(record);
  const [values, setValues] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [checkError, setCheckError] = useState(null);
  const [checkPending, setCheckPending] = useState(false);
  const mutation = useWrite();
  // Lỗi xác nhận kiểm tra chỉ hiện trong hộp xác nhận, không lặp lại ở chi tiết.
  const checkMutation = useWrite();
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
  // UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 2–8; A5 xem trước rồi xác nhận (specs/use_cases/production/UC-26.md)
  async function openCheck() {
    setCheckError(null);
    setCheckPending(true);
    const etag = snapshot.etag;
    try {
      const { data: ketQua } = await readResource(`${API.requests}/${record.id}/kiem_tra`);
      confirm({
        title: ketQua.lan_dau ? "Kiểm tra yêu cầu sản xuất" : "Kiểm tra lại yêu cầu sản xuất",
        description: record.ma_yeu_cau_san_xuat,
        content: <>
          <InfoGrid entries={checkConfirmEntries(ketQua, record.loai_yeu_cau)} />
          <DataTable rows={checkLines(ketQua)} columns={CHECK_COLUMNS} />
        </>,
        impact: checkImpact(ketQua),
        onConfirm: async () => {
          const result = await checkMutation.mutateAsync({
            path: `${API.requests}/${record.id}/kiem_tra`,
            body: {},
            etag,
          });
          const actual = result.data.ket_qua;
          onCheckResult(actual);
          notify(actual.du_linh_kien ? "Yêu cầu Đang thực hiện."
            : actual.lan_dau ? "Yêu cầu Chờ bổ sung linh kiện." : "Vẫn thiếu linh kiện.");
        },
      });
    } catch (failure) {
      setCheckError(failure);
    } finally {
      setCheckPending(false);
    }
  }
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
      <ErrorNotice error={checkError} />
      {checkResult && !checkResult.du_linh_kien && (
        <>
          <Notice tone="warning">Yêu cầu Chờ bổ sung linh kiện.</Notice>
          <h3>Linh kiện thiếu</h3>
          <DataTable rows={checkLines(checkResult).filter((line) => line.so_luong_thieu > 0)} columns={CHECK_COLUMNS} />
        </>
      )}
      {canCheckRequest(record, manager, userId) && (
        <div className="actions actions-end">
          <Button disabled={checkMutation.isPending || checkPending} onClick={openCheck}>
            {record.trang_thai === "da_gui" ? "Kiểm tra" : "Kiểm tra lại"}
          </Button>
        </div>
      )}
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
