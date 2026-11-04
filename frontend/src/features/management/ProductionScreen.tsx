import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, ClipboardList, Factory, GitBranch, Save, ShieldCheck } from "lucide-react";
import { ActionButton, Field, FormError, Notice, PageTitle, Panel, Status } from "./components";
import { itemById, number } from "./planning";
import type { OrderStatus } from "./types";
import { useWorkspace, useWorkspaceMutation } from "./workspace-hooks";

const orderLabels: Record<OrderStatus, string> = {
  nhap: "Nháp",
  da_gui: "Đã gửi",
  dang_thuc_hien: "Đang thực hiện",
  hoan_thanh: "Hoàn thành",
  da_huy: "Đã hủy",
};

export function ProductionScreen() {
  const { workspace, notify } = useWorkspace();
  const [params] = useSearchParams();
  const [requestId, setRequestId] = useState(params.get("request") ?? "");
  const [orderId, setOrderId] = useState("");
  const [assignment, setAssignment] = useState<{ orderId: string; assigneeId: string } | null>(
    null,
  );
  const assign = useWorkspaceMutation((api, input: { id: string; assigneeId: string | null }) =>
    api.assignOrder(input),
  );
  const send = useWorkspaceMutation((api, id: string) => api.sendOrder(id));
  const orders = workspace.orders.filter((order) => !requestId || order.requestId === requestId);
  const order = orders.find((entry) => entry.id === orderId) ?? orders[0];
  const employees = workspace.employees.filter(
    (employee) => employee.active && employee.role === "nhan_vien",
  );
  const busy = assign.isPending || send.isPending;

  function chooseOrder(id: string) {
    setOrderId(id);
    setAssignment(null);
    assign.reset();
    send.reset();
  }

  async function saveAssignment() {
    if (!order) return;
    try {
      const assigneeId =
        assignment?.orderId === order.id ? assignment.assigneeId : order.assigneeId;
      const result = await assign.mutateAsync({ id: order.id, assigneeId: assigneeId || null });
      setAssignment(null);
      notify(
        `Đã lưu phân công ${result.code}`,
        "Chỉ cập nhật người thực hiện. Lượng, BOM và nhu cầu của lệnh giữ nguyên.",
      );
    } catch {
      /* The mutation error is displayed beside the assignment. */
    }
  }

  async function sendOrder() {
    if (!order) return;
    try {
      const result = await send.mutateAsync(order.id);
      notify(
        `Đã gửi ${result.code}`,
        "Nhân viên được giao có thể xem công việc. Gửi lệnh không thay đổi tồn kho.",
      );
    } catch {
      /* The mutation error is displayed beside the assignment. */
    }
  }

  const heading = (
    <PageTitle
      step="03 / 04"
      title="Lệnh sản xuất"
      description="Phân công và gửi các lệnh được sinh từ kế hoạch yêu cầu."
    />
  );

  if (!order) {
    return (
      <>
        {heading}
        <Panel title="Chưa có lệnh trong yêu cầu này">
          <div className="m-panel-body">
            <Notice>
              Lệnh được tạo tự động khi gửi yêu cầu. Nếu đủ tồn thành phẩm, kế hoạch không cần tạo
              lệnh sản xuất.
            </Notice>
            <Link className="m-text-link" to="/quan-ly/yeu-cau-thanh-pham">
              Đến yêu cầu thành phẩm <ArrowRight size={16} />
            </Link>
            {requestId && (
              <ActionButton onClick={() => setRequestId("")}>Xem tất cả lệnh</ActionButton>
            )}
          </div>
        </Panel>
      </>
    );
  }

  const request = workspace.requests.find((entry) => entry.id === order.requestId)!;
  const output = itemById(workspace.items, order.outputId);
  const bom = workspace.boms.find((entry) => entry.id === order.bomId)!;
  const parent = workspace.orders.find((entry) => entry.id === order.parentOrderId);
  const assigneeId =
    assignment?.orderId === order.id ? assignment.assigneeId : (order.assigneeId ?? "");
  const changed = assigneeId !== (order.assigneeId ?? "");
  const locked = order.status !== "nhap";
  const demand = order.demand.map((line) => {
    const item = itemById(workspace.items, line.itemId);
    const issued = workspace.issues
      .filter((issue) => issue.orderId === order.id && issue.status === "da_duyet")
      .reduce(
        (sum, issue) =>
          sum +
          issue.lines
            .filter((entry) => entry.itemId === line.itemId)
            .reduce((total, entry) => total + entry.quantity, 0),
        0,
      );
    return { ...line, item, issued, remaining: Math.max(0, line.required - issued) };
  });
  const shortages = demand.filter((line) => line.remaining > line.item.stock).length;
  const children = workspace.orders.filter((entry) => entry.parentOrderId === order.id);
  const worker = workspace.employees.find((entry) => entry.id === order.assigneeId);

  return (
    <>
      {heading}
      <div className="m-document-bar">
        <div>
          <span className="m-document-code">{order.code}</span>
          <Status tone={order.status === "hoan_thanh" ? "green" : "neutral"}>
            {orderLabels[order.status]}
          </Status>
        </div>
        <span className="m-icon-label">
          <GitBranch size={16} />
          {parent ? "Lệnh con" : "Lệnh gốc"}
        </span>
      </div>
      <div className="m-work-grid">
        <div className="m-main-stack">
          <Panel
            title="Lệnh từ kế hoạch đã gửi"
            subtitle="Số lượng, đầu ra, BOM và quan hệ cha con đã được lưu cùng kế hoạch."
          >
            <div className="m-panel-body m-fields">
              <Field label="Lọc theo yêu cầu">
                <select
                  value={requestId}
                  disabled={busy}
                  onChange={(event) => {
                    setRequestId(event.target.value);
                    chooseOrder("");
                  }}
                >
                  <option value="">Tất cả yêu cầu</option>
                  {workspace.requests.map((entry) => (
                    <option key={entry.id} value={entry.id}>
                      {entry.code} · {itemById(workspace.items, entry.productId).name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Chọn lệnh sản xuất">
                <select
                  value={order.id}
                  disabled={busy}
                  onChange={(event) => chooseOrder(event.target.value)}
                >
                  {orders.map((entry) => (
                    <option key={entry.id} value={entry.id}>
                      {entry.code} · {itemById(workspace.items, entry.outputId).name} ·{" "}
                      {orderLabels[entry.status]}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Mặt hàng đầu ra">
                <input value={`${output.code} · ${output.name}`} readOnly />
              </Field>
              <Field label="Số lượng sản xuất">
                <input value={`${number(order.quantity)} ${output.unit}`} readOnly />
              </Field>
              <Field label="BOM đã chốt">
                <input value={`${output.code} · Phiên bản ${bom.version}`} readOnly />
              </Field>
              <Field label="Lệnh cha">
                <input value={parent?.code ?? "Không có · Lệnh gốc của yêu cầu"} readOnly />
              </Field>
              <Field label="Ngày tạo">
                <input value={new Date(order.createdAt).toLocaleString("vi-VN")} readOnly />
              </Field>
              <Field label="Trạng thái">
                <input value={orderLabels[order.status]} readOnly />
              </Field>
            </div>
          </Panel>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void saveAssignment();
            }}
          >
            <Panel
              title="Phân công thực hiện"
              subtitle="Chỉ lệnh nháp được đổi nhân viên. Gửi lệnh cần nhân viên đang hoạt động."
            >
              <fieldset disabled={locked || busy} className="m-panel-body m-fields">
                <Field label="Nhân viên thực hiện" wide hint="Có thể để trống khi còn nháp.">
                  <select
                    value={assigneeId}
                    onChange={(event) => {
                      setAssignment({ orderId: order.id, assigneeId: event.target.value });
                      assign.reset();
                      send.reset();
                    }}
                  >
                    <option value="">Chưa giao nhân viên</option>
                    {employees.map((employee) => (
                      <option key={employee.id} value={employee.id}>
                        {employee.code} · {employee.name}
                      </option>
                    ))}
                  </select>
                </Field>
              </fieldset>
              <div className="m-panel-body m-panel-body--topless">
                <FormError error={assign.error ?? send.error} />
                <Notice tone={shortages ? "amber" : "neutral"}>
                  {locked
                    ? `Lệnh ${orderLabels[order.status].toLocaleLowerCase("vi-VN")} · ${worker?.name ?? "Chưa có nhân viên được giao"}.`
                    : shortages
                      ? "Thiếu vật tư không chặn gửi lệnh. Nhân viên chỉ bắt đầu khi mọi vật tư đã được cấp đủ."
                      : "Gửi lệnh chuyển sang Đã gửi; không trừ vật tư hoặc cộng thành phẩm."}
                </Notice>
              </div>
              <footer className="m-action-bar">
                <span>
                  <ShieldCheck size={16} />
                  {changed ? "Lưu phân công trước khi gửi" : "Tồn kho không đổi khi gửi lệnh"}
                </span>
                <div>
                  <ActionButton type="submit" disabled={locked || busy || !changed}>
                    <Save size={16} />
                    {assign.isPending ? "Đang lưu…" : "Lưu phân công"}
                  </ActionButton>
                  <ActionButton
                    variant="primary"
                    disabled={locked || busy || changed || !assigneeId}
                    onClick={() => void sendOrder()}
                  >
                    {send.isPending ? "Đang gửi…" : "Gửi lệnh"}
                    <ArrowRight size={16} />
                  </ActionButton>
                </div>
              </footer>
            </Panel>
          </form>
          <Panel
            title="Nhu cầu trực tiếp đã chốt"
            subtitle="Đọc từ ảnh chụp định mức của lệnh; không phân rã lại theo BOM mới."
            action={
              <Status tone={shortages ? "amber" : "neutral"}>
                {shortages ? `${shortages} loại chưa đủ tồn` : "Tồn đáp ứng phần chưa cấp"}
              </Status>
            }
          >
            <div className="m-table-scroll">
              <table className="m-table">
                <thead>
                  <tr>
                    <th>Vật tư</th>
                    <th className="m-number">Cần cấp</th>
                    <th className="m-number">Đã cấp</th>
                    <th className="m-number">Còn cần cấp</th>
                    <th className="m-number">Tồn hiện tại</th>
                  </tr>
                </thead>
                <tbody>
                  {demand.map((line) => (
                    <tr key={line.itemId}>
                      <td>
                        <strong>{line.item.name}</strong>
                        <small>
                          {line.item.code} · {line.item.unit}
                        </small>
                      </td>
                      <td className="m-number">{number(line.required)}</td>
                      <td className="m-number">{number(line.issued)}</td>
                      <td className="m-number">{number(line.remaining)}</td>
                      <td
                        className={`m-number ${line.remaining > line.item.stock ? "m-shortage" : ""}`}
                      >
                        {number(line.item.stock)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="m-panel-body">
              <Notice>
                Chỉ phiếu xuất vật tư đã duyệt mới được tính là đã cấp. Bắt đầu và hoàn thành lệnh
                thuộc luồng công việc của nhân viên.
              </Notice>
            </div>
          </Panel>
        </div>
        <aside className="m-side-stack">
          <Panel title="Yêu cầu và cây lệnh">
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
                  <dt>Cần đáp ứng</dt>
                  <dd>{number(request.quantity)} xe</dd>
                </div>
                <div>
                  <dt>Lệnh cha</dt>
                  <dd>{parent?.code ?? "Không có"}</dd>
                </div>
                <div>
                  <dt>Lệnh con</dt>
                  <dd>{children.length}</dd>
                </div>
              </dl>
              {parent && (
                <ActionButton variant="plain" onClick={() => chooseOrder(parent.id)}>
                  Xem {parent.code}
                  <ArrowRight size={14} />
                </ActionButton>
              )}
              {children.map((child) => (
                <ActionButton key={child.id} variant="plain" onClick={() => chooseOrder(child.id)}>
                  Xem {child.code}
                  <ArrowRight size={14} />
                </ActionButton>
              ))}
              <Link className="m-text-link" to="/quan-ly/yeu-cau-thanh-pham">
                Tạo yêu cầu khác
                <ArrowRight size={15} />
              </Link>
            </div>
          </Panel>
          <Panel title="Từ kế hoạch đến sản xuất">
            <ol className="m-process-list">
              <li className="is-current">
                <span>1</span>
                <div>
                  <strong>Gửi yêu cầu</strong>
                  <small>Tự sinh cây lệnh nháp theo BOM</small>
                </div>
              </li>
              <li>
                <span>2</span>
                <div>
                  <strong>Phân công và gửi lệnh</strong>
                  <small>Quản lý giao việc cho nhân viên</small>
                </div>
              </li>
              <li>
                <span>3</span>
                <div>
                  <strong>Cấp vật tư</strong>
                  <small>Quản lý lập và duyệt phiếu xuất</small>
                </div>
              </li>
              <li>
                <span>4</span>
                <div>
                  <strong>Thực hiện và hoàn thành</strong>
                  <small>Nhân viên lập chứng từ hoàn thành</small>
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
          <div className="m-rule-note">
            <Factory size={20} strokeWidth={1.5} />
            <strong>Lệnh giữ nguyên kế hoạch</strong>
            <p>
              Mỗi lệnh gắn đúng mặt hàng, phiên bản BOM và yêu cầu đã gửi. Lệnh con nhập đầu ra
              trước khi cấp bán thành phẩm cho lệnh cha.
            </p>
          </div>
        </aside>
      </div>
    </>
  );
}
