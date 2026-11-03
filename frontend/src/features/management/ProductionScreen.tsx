import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  Check,
  ClipboardList,
  Factory,
  FilePlus2,
  Layers,
  ShieldCheck,
} from "lucide-react";
import {
  ActionButton,
  Field,
  FormError,
  MaterialTable,
  Notice,
  PageTitle,
  Panel,
  Status,
} from "./components";
import { itemById, materialDemand, number } from "./planning";
import { employees } from "./types";
import type { OrderKind, WorkOrder, WorkOrderInput } from "./types";
import { useWorkspace, useWorkspaceMutation } from "./workspace-hooks";

export function ProductionScreen() {
  const { workspace, notify } = useWorkspace();
  const [params] = useSearchParams();
  const initialRequest =
    workspace.requests.find((entry) => entry.id === params.get("request")) ??
    workspace.requests[workspace.requests.length - 1];
  const [requestId, setRequestId] = useState(initialRequest.id);
  const [kind, setKind] = useState<OrderKind>("bike");
  const [quantity, setQuantity] = useState(() =>
    Math.max(
      0,
      initialRequest.plan.bikesToMake -
        workspace.orders
          .filter((order) => order.requestId === initialRequest.id && order.kind === "bike")
          .reduce((sum, order) => sum + order.quantity, 0),
    ),
  );
  const [assignee, setAssignee] = useState<string>(initialRequest.assignee);
  const [note, setNote] = useState("");
  const [created, setCreated] = useState<WorkOrder | null>(null);
  const request = workspace.requests.find((entry) => entry.id === requestId) ?? initialRequest;
  const output = itemById(workspace.items, kind === "bike" ? request.productId : "wheel");
  const planned = kind === "bike" ? request.plan.bikesToMake : request.plan.wheelsToMake;
  const ordered = workspace.orders
    .filter((order) => order.requestId === requestId && order.kind === kind)
    .reduce((total, order) => total + order.quantity, 0);
  const remaining = Math.max(0, planned - ordered);
  const lines = materialDemand(
    workspace.items,
    kind,
    Number.isSafeInteger(quantity) && quantity > 0 ? quantity : 0,
  );
  const missing = lines.filter((line) => line.missing > 0).length;
  const create = useWorkspaceMutation((api, input: WorkOrderInput) => api.createOrder(input));

  function chooseKind(next: OrderKind) {
    setKind(next);
    setCreated(null);
    create.reset();
    const demand = next === "bike" ? request.plan.bikesToMake : request.plan.wheelsToMake;
    const existing = workspace.orders
      .filter((order) => order.requestId === requestId && order.kind === next)
      .reduce((sum, order) => sum + order.quantity, 0);
    setQuantity(Math.max(0, demand - existing));
  }

  async function submit() {
    try {
      const result = await create.mutateAsync({ requestId, kind, quantity, assignee, note });
      setCreated(result);
      notify(
        `Đã tạo ${result.code}`,
        `Giao ${assignee} sản xuất ${number(result.quantity)} ${output.unit}. Tồn kho giữ nguyên.`,
      );
    } catch {
      /* Show the command error below the form. */
    }
  }

  return (
    <>
      <PageTitle
        step="03 / 04"
        title="Lệnh sản xuất"
        description="Chuyển nhu cầu còn thiếu thành công việc cho xưởng."
        action={
          created ? (
            <ActionButton
              onClick={() => {
                setCreated(null);
                setNote("");
                setQuantity(remaining);
                create.reset();
              }}
            >
              <FilePlus2 size={16} />
              Lệnh mới
            </ActionButton>
          ) : undefined
        }
      />
      <div className="m-kind-tabs" role="group" aria-label="Loại lệnh sản xuất">
        <button aria-pressed={kind === "bike"} onClick={() => chooseKind("bike")}>
          <Factory size={17} />
          Lệnh lắp xe
        </button>
        <button aria-pressed={kind === "wheel"} onClick={() => chooseKind("wheel")}>
          <Layers size={17} />
          Lệnh cụm bánh
        </button>
      </div>
      <div className="m-work-grid">
        <form
          className="m-main-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <Panel
            title="Thông tin lệnh sản xuất"
            subtitle="Liên kết yêu cầu, xác định đầu ra và người thực hiện."
            action={
              <Status tone={created ? "green" : "neutral"}>{created?.code ?? "Chưa tạo"}</Status>
            }
          >
            <fieldset className="m-panel-body m-fields" disabled={!!created || create.isPending}>
              <Field label="Yêu cầu thành phẩm" required wide>
                <select
                  value={requestId}
                  onChange={(event) => {
                    const next = workspace.requests.find(
                      (entry) => entry.id === event.target.value,
                    );
                    if (!next) return;
                    setRequestId(next.id);
                    setAssignee(next.assignee);
                    const total = kind === "bike" ? next.plan.bikesToMake : next.plan.wheelsToMake;
                    const existing = workspace.orders
                      .filter((order) => order.requestId === next.id && order.kind === kind)
                      .reduce((sum, order) => sum + order.quantity, 0);
                    setQuantity(Math.max(0, total - existing));
                  }}
                >
                  {workspace.requests.map((entry) => (
                    <option key={entry.id} value={entry.id}>
                      {entry.code} · {itemById(workspace.items, entry.productId).name} ·{" "}
                      {entry.quantity} xe
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Thành phẩm đầu ra">
                <input value={`${output.code} · ${output.name}`} readOnly />
              </Field>
              <Field
                label="Số lượng cần sản xuất"
                required
                hint={`${created ? "Đã tạo" : "Chưa tạo lệnh"}: ${number(created ? created.quantity : remaining)} ${output.unit}`}
              >
                <input
                  type="number"
                  min={1}
                  max={created ? created.quantity : remaining || 1}
                  step={1}
                  required
                  value={Number.isNaN(quantity) ? "" : quantity}
                  onChange={(event) => setQuantity(event.target.valueAsNumber)}
                />
              </Field>
              <Field label="Nhân viên thực hiện" required>
                <select value={assignee} onChange={(event) => setAssignee(event.target.value)}>
                  {employees.map((name) => (
                    <option key={name}>{name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Loại công việc">
                <input
                  readOnly
                  value={kind === "bike" ? "Lắp ráp xe thành phẩm" : "Sản xuất cụm bánh xe"}
                />
              </Field>
              <Field label="Chỉ dẫn sản xuất" wide>
                <textarea
                  rows={2}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Ghi rõ thứ tự ưu tiên hoặc lưu ý cho nhân viên…"
                />
              </Field>
            </fieldset>
          </Panel>
          <Panel
            title="Định mức cấp vật tư"
            subtitle={`Nhu cầu cho ${number(Number.isFinite(quantity) ? quantity : 0)} ${output.unit} ${output.name}.`}
            action={
              <Status tone={missing ? "amber" : "green"}>
                {missing ? `${missing} loại còn thiếu` : "Vật tư sẵn sàng"}
              </Status>
            }
          >
            <MaterialTable items={workspace.items} lines={lines} />
            <div className="m-panel-body">
              <Notice tone={missing ? "amber" : "neutral"}>
                {missing
                  ? "Có thể tạo lệnh dù vật tư chưa đủ. Nhân viên cần được cấp đủ vật tư trước khi bắt đầu sản xuất."
                  : "Định mức dùng để lập đề nghị xuất. Tạo lệnh không trừ vật tư và không cộng thành phẩm."}
              </Notice>
            </div>
            <FormError error={create.error} />
            {created && (
              <div className="m-success-card">
                <Check size={20} />
                <div>
                  <strong>{created.code} đã được tạo</strong>
                  <p>
                    {assignee} · {number(created.quantity)} {output.unit} {output.name}
                  </p>
                </div>
                <Status tone={missing ? "amber" : "neutral"}>Chờ cấp vật tư</Status>
              </div>
            )}
            {!created && remaining === 0 && (
              <div className="m-panel-body">
                <Notice>
                  Phần nhu cầu này đã được tạo đủ lệnh hoặc không cần sản xuất thêm. Anh có thể chọn
                  yêu cầu hoặc loại lệnh khác.
                </Notice>
              </div>
            )}
            <footer className="m-action-bar">
              <span>
                <ShieldCheck size={16} />
                Tồn kho không đổi khi tạo lệnh
              </span>
              <div>
                <ActionButton
                  type="submit"
                  variant="primary"
                  disabled={!!created || create.isPending || remaining === 0}
                >
                  {create.isPending ? "Đang tạo…" : "Tạo lệnh sản xuất"}
                  <ArrowRight size={16} />
                </ActionButton>
              </div>
            </footer>
          </Panel>
        </form>
        <aside className="m-side-stack">
          <Panel title="Nhu cầu liên quan">
            <div className="m-panel-body">
              <div className="m-linked-document">
                <ClipboardList size={21} />
                <div>
                  <strong>{request.code}</strong>
                  <span>{itemById(workspace.items, request.productId).name}</span>
                </div>
              </div>
              <dl className="m-summary-list">
                <div>
                  <dt>Tổng cần đáp ứng</dt>
                  <dd>{number(request.quantity)} xe</dd>
                </div>
                <div>
                  <dt>Xe cần lắp</dt>
                  <dd>{number(request.plan.bikesToMake)} xe</dd>
                </div>
                <div>
                  <dt>Cụm bánh cần làm</dt>
                  <dd>{number(request.plan.wheelsToMake)} cụm</dd>
                </div>
                <div>
                  <dt>Đã tạo lệnh loại này</dt>
                  <dd>
                    {number(ordered)} {output.unit}
                  </dd>
                </div>
              </dl>
              <Link className="m-text-link" to="/quan-ly/yeu-cau-thanh-pham">
                Tạo yêu cầu khác
                <ArrowRight size={15} />
              </Link>
            </div>
          </Panel>
          <Panel title="Sau khi tạo lệnh">
            <ol className="m-process-list">
              <li className="is-current">
                <span>1</span>
                <div>
                  <strong>Tạo lệnh sản xuất</strong>
                  <small>Quản lý giao việc cho nhân viên</small>
                </div>
              </li>
              <li>
                <span>2</span>
                <div>
                  <strong>Đề nghị xuất vật tư</strong>
                  <small>Nhân viên lập phiếu xuất</small>
                </div>
              </li>
              <li>
                <span>3</span>
                <div>
                  <strong>Duyệt cấp vật tư</strong>
                  <small>Kiểm tra tồn trước khi ghi sổ</small>
                </div>
              </li>
              <li>
                <span>4</span>
                <div>
                  <strong>Sản xuất và hoàn thành</strong>
                  <small>Gửi chứng từ hoàn thành</small>
                </div>
              </li>
            </ol>
            <div className="m-panel-body m-panel-body--topless">
              <Link className="m-text-link" to="/quan-ly/duyet-phieu-xuat">
                Đến hàng chờ duyệt
                <ArrowRight size={15} />
              </Link>
            </div>
          </Panel>
          {workspace.orders.length > 0 && (
            <Panel title="Lệnh vừa tạo">
              <div className="m-recent-list">
                {[...workspace.orders]
                  .reverse()
                  .slice(0, 3)
                  .map((order) => (
                    <div key={order.id}>
                      <strong>{order.code}</strong>
                      <span>
                        {order.quantity} {itemById(workspace.items, order.outputId).unit} ·{" "}
                        {order.assignee}
                      </span>
                    </div>
                  ))}
              </div>
            </Panel>
          )}
        </aside>
      </div>
    </>
  );
}
