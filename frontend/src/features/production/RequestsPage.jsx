import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { readResource } from "../../lib/api/client.js";
import {
  useCatalog,
  useChoices,
  useCollection,
  useDetail,
  useResource,
  useWrite,
} from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { itemName, formatDate, number } from "../../lib/format.js";
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
  CANCEL_HOLD_COLUMNS,
  CANCEL_ISSUE_COLUMNS,
  cancelConfirmEntries,
  canCheckRequest,
  canStartProduction,
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
import {
  canApproveCompletion,
  approveConfirmEntries,
  approveImpact,
  canCreateCompletion,
  canSendCompletion,
  completionEntries,
  completionConfirmEntries,
  completionSendLabel,
} from "./completionForm.js";
import { canCreateIssue } from "../material-issuing/issueForm.js";

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
        expandableFilters={!manager}
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
            render: (row) => <Link to={`${base}/${row.id}`}>{manager ? "Mở →" : "Mở"}</Link>,
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
  const [startError, setStartError] = useState(null);
  const [checkPending, setCheckPending] = useState(false);
  const [cancelError, setCancelError] = useState(null);
  const [cancelPending, setCancelPending] = useState(false);
  const mutation = useWrite();
  // Lỗi xác nhận kiểm tra chỉ hiện trong hộp xác nhận, không lặp lại ở chi tiết.
  const checkMutation = useWrite();
  const cancelMutation = useWrite();
  const startMutation = useWrite();
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
  // UC-29 Bắt đầu sản xuất — Main 2–5; A1 ghi ngay với ETag và báo lỗi riêng (specs/use_cases/production/UC-29.md)
  async function start() {
    setStartError(null);
    try {
      await startMutation.mutateAsync({
        path: `${API.requests}/${record.id}/bat_dau`,
        body: {},
        etag: snapshot.etag,
      });
      notify("Đã ghi nhận bắt đầu sản xuất.");
    } catch (failure) {
      setStartError(failure);
    }
  }
  // UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 2–8; A5 xem trước rồi xác nhận (specs/use_cases/production/UC-26.md)
  async function openCheck() {
    setCheckError(null);
    setCheckPending(true);
    const etag = snapshot.etag;
    try {
      const { data: ketQua } = await readResource(`${API.requests}/${record.id}/kiem_tra`);
      confirm({
        title: ketQua.lan_dau ? "Kiểm tra yêu cầu sản xuất" : "Kiểm tra lại yêu cầu sản xuất",
        variant: "request-check",
        description: record.ma_yeu_cau_san_xuat,
        content: <>
          <InfoGrid entries={checkConfirmEntries(ketQua, record.loai_yeu_cau)} />
          <div className="request-check-table"><DataTable rows={checkLines(ketQua)} columns={CHECK_COLUMNS} /></div>
          <RequestCheckCards rows={checkLines(ketQua)} />
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
  // UC-28 Hủy yêu cầu sản xuất — Main 2–5; A2, A3 xem trước rồi xác nhận hủy (specs/use_cases/production/UC-28.md)
  function cancel(remove = false) {
    if (remove) {
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
      return;
    }
    return (async () => {
      setCancelError(null);
      setCancelPending(true);
      const etag = snapshot.etag;
      try {
        const { data: cancellation } = await readResource(`${API.requests}/${record.id}/huy`);
        if (!cancellation.duoc_huy) {
          setCancelError(new Error(cancellation.ly_do_khong_huy));
          return;
        }
        const entries = cancelConfirmEntries(cancellation);
        confirm({
          title: "Hủy yêu cầu sản xuất",
          description: record.ma_yeu_cau_san_xuat,
          reason: true,
          danger: true,
          content: <>
            <h3>Hàng sẽ trả lại</h3>
            <DataTable rows={entries.hang_tra} columns={CANCEL_HOLD_COLUMNS} empty="Không có hàng đang giữ." />
            <h3>Phiếu xuất bị ảnh hưởng</h3>
            <DataTable rows={entries.phieu_xuat} columns={CANCEL_ISSUE_COLUMNS} empty="Không có phiếu xuất chưa duyệt." />
          </>,
          impact: "Tồn thực tế không đổi.",
          onConfirm: async (reason) => {
            await cancelMutation.mutateAsync({
              path: `${API.requests}/${record.id}/huy`,
              body: { ly_do: reason },
              etag,
            });
            notify("Đã hủy yêu cầu.");
          },
        });
      } catch (failure) {
        setCancelError(failure);
      } finally {
        setCancelPending(false);
      }
    })();
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
          <CompletionSection record={record} items={items} manager={manager} userId={userId} />
          {!manager && <IssueLinks record={record} userId={userId} />}
        </>
      )}
      <ErrorNotice error={(showForm && error) || mutation.error} />
      <ErrorNotice error={checkError} />
      <ErrorNotice error={startError} />
      <ErrorNotice error={cancelError} />
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
      {canStartProduction(record, manager, userId) && (
        <div className="actions actions-end">
          <Button disabled={startMutation.isPending} onClick={start}>Bắt đầu sản xuất</Button>
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
          <Button variant="secondary" disabled={cancelPending || cancelMutation.isPending} onClick={() => cancel()}>
            Hủy yêu cầu…
          </Button>
        </div>
      )}
    </div>
  );
}

function RequestCheckCards({ rows }) {
  return <div className="request-check-cards">
      {rows.length ? rows.map((line) => <section key={line.id} aria-label={`Linh kiện ${line.ma_mat_hang}`}>
        <InfoGrid entries={CHECK_COLUMNS.map((column) => [column.label, line[column.key]])} />
      </section>) : <Notice>Chưa có dữ liệu phù hợp.</Notice>}
    </div>;
}

function IssueLinks({ record, userId }) {
  const issues = useResource(`${API.issues}/theo_yeu_cau/${record.id}`, {}, record.nhan_vien_duoc_giao_id === userId);
  const completion = useResource(`${API.requests}/${record.id}/chung_tu_hoan_thanh`, {},
    Boolean(record.nhan_vien_duoc_giao_id === userId && record.started_at && record.so_luong_can_san_xuat > 0));
  if (record.nhan_vien_duoc_giao_id !== userId) return null;
  const saved = issues.data?.data || [];
  return <QueryState query={issues}><div className="actions actions-end">
    {saved.map((issue) => <Link key={issue.id} className="btn btn-secondary"
      to={`/nv/${issue.loai_phieu === "xuat_linh_kien" ? "xuat-nvl" : "xuat-tp"}/${issue.id}`}>
      Mở phiếu {issue.ma_phieu_xuat}
    </Link>)}
    {!saved.some((issue) => issue.loai_phieu === "xuat_linh_kien") && canCreateIssue(record, "xuat_linh_kien", userId, completion.data?.data) && (
      <Link className="btn btn-secondary" to={`/nv/xuat-nvl/moi?yeu_cau_san_xuat_id=${record.id}`}>Lập phiếu xuất linh kiện</Link>
    )}
    {!saved.some((issue) => issue.loai_phieu === "xuat_thanh_pham") && canCreateIssue(record, "xuat_thanh_pham", userId, completion.data?.data) && (
      <Link className="btn btn-secondary" to={`/nv/xuat-tp/moi?yeu_cau_san_xuat_id=${record.id}`}>Lập phiếu xuất thành phẩm</Link>
    )}
  </div></QueryState>;
}

function CompletionSection({ record, items, manager, userId }) {
  // Chứng từ chỉ có sau khi bắt đầu sản xuất; không đọc với yêu cầu chưa bắt đầu.
  const query = useResource(`${API.requests}/${record.id}/chung_tu_hoan_thanh`, {}, Boolean(record.id && record.started_at));
  const completion = query.data?.data;
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);
  const completionMutation = useWrite();
  const { confirm, notify } = useFeedback();
  const canCreate = canCreateCompletion(record, completion, manager, userId);
  const canSend = canSendCompletion(record, completion, manager, userId);
  const canApprove = canApproveCompletion(completion, record, manager);

  // UC-31 Duyệt chứng từ hoàn thành sản xuất — Main 2–6; A1 xác nhận mới POST với ETag chứng từ đã xem (specs/use_cases/production/UC-31.md)
  function approve() {
    const etag = query.data.etag;
    confirm({
      title: "Duyệt chứng từ hoàn thành",
      description: completion.ma_phieu,
      content: <InfoGrid entries={approveConfirmEntries(completion, record, items)} />,
      impact: approveImpact(completion, record),
      onConfirm: async () => {
        await completionMutation.mutateAsync({
          path: [API.completions, completion.id, "duyet"].join("/"),
          body: {},
          etag,
        });
        notify("Đã duyệt chứng từ hoàn thành.");
      },
    });
  }

  // UC-32 Từ chối chứng từ hoàn thành sản xuất — Main 2–5; A1, A2 (specs/use_cases/production/UC-32.md)
  function rejectCompletion() {
    const etag = query.data.etag;
    confirm({
      title: "Từ chối chứng từ hoàn thành",
      description: completion.ma_phieu,
      reason: true,
      danger: true,
      impact: "Tồn không đổi; nhân viên sẽ gửi lại chứng từ.",
      onConfirm: async (ly_do) => {
        await completionMutation.mutateAsync({
          path: [API.completions, completion.id, "tu_choi"].join("/"),
          body: { ly_do },
          etag,
        });
        notify("Đã từ chối chứng từ hoàn thành.");
      },
    });
  }

  // UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 2–3 mở biểu mẫu chỉ đọc (specs/use_cases/production/UC-30.md)
  function openCompletion() {
    setCreateError(null);
    setCreating(true);
  }

  // UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 4–5 lưu Nháp (specs/use_cases/production/UC-30.md)
  async function saveCompletion() {
    setCreateError(null);
    try {
      await completionMutation.mutateAsync({
        path: API.completions,
        body: { yeu_cau_san_xuat_id: record.id },
        versioned: false,
      });
      setCreating(false);
      notify("Đã lưu chứng từ hoàn thành.");
    } catch (failure) {
      setCreateError(failure);
    }
  }

  // UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 6–9; A2, A3 xác nhận mới gửi (specs/use_cases/production/UC-30.md)
  function sendCompletion() {
    const etag = query.data.etag;
    confirm({
      title: completion.trang_thai === "tu_choi" ? "Gửi lại chứng từ hoàn thành" : "Gửi chứng từ hoàn thành",
      description: completion.ma_phieu,
      content: <InfoGrid entries={completionConfirmEntries(completion, record, items)} />,
      impact: "Chưa cộng tồn thành phẩm.",
      onConfirm: async () => {
        await completionMutation.mutateAsync({
          path: [API.completions, completion.id, "gui"].join("/"),
          body: {},
          etag,
        });
        notify("Đã gửi chứng từ hoàn thành.");
      },
    });
  }

  if (!record.started_at && !completion) return null;
  return (
    <section className="stack">
      <h3>Chứng từ hoàn thành sản xuất</h3>
      <QueryState query={query}>
        <ErrorNotice error={createError} />
        {completion ? (
          <InfoGrid entries={completionEntries(completion).map(([label, value]) => [
            label, label === "Trạng thái" ? <Badge status={value} /> : value,
          ])} />
        ) : !canCreate ? (
          <Notice>Chưa có chứng từ hoàn thành.</Notice>
        ) : (creating ? (
          <>
            <InfoGrid entries={[["Số lượng hoàn thành", number(record.so_luong_can_san_xuat)]]} />
            <Notice>Thời điểm hoàn thành do hệ thống ghi khi bạn xác nhận gửi.</Notice>
            <div className="actions actions-end">
              <Button variant="secondary" disabled={completionMutation.isPending} onClick={() => setCreating(false)}>Bỏ</Button>
              <Button disabled={completionMutation.isPending} onClick={saveCompletion}>Lưu</Button>
            </div>
          </>
        ) : (
          <div className="actions actions-end">
            <Button disabled={completionMutation.isPending} onClick={openCompletion}>Lập chứng từ hoàn thành</Button>
          </div>
        ))}
        {canSend && (
          <div className="actions actions-end">
            <Button disabled={completionMutation.isPending} onClick={sendCompletion}>{completionSendLabel(completion)}</Button>
          </div>
        )}
        {canApprove && (
          <div className="actions actions-end">
            <Button variant="secondary" disabled={completionMutation.isPending} onClick={rejectCompletion}>Từ chối</Button>
            <Button disabled={completionMutation.isPending} onClick={approve}>Duyệt</Button>
          </div>
        )}
      </QueryState>
    </section>
  );
}
