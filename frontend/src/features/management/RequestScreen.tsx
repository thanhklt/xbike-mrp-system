import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowDown,
  ArrowRight,
  Bike,
  Check,
  FilePlus2,
  GitBranch,
  Package,
  RefreshCw,
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
import { calculatePlan, itemById, number } from "./planning";
import { currentManager } from "./types";
import type {
  ProductionPlan,
  ProductionRequest,
  RequestInput,
  RequestPreview,
  RequestStatus,
} from "./types";
import { useWorkspace, useWorkspaceMutation } from "./workspace-hooks";

const requestLabels: Record<RequestStatus, string> = {
  nhap: "Nháp",
  da_gui: "Đã gửi",
  cho_bo_sung_vat_tu: "Chờ bổ sung vật tư",
  dang_thuc_hien: "Đang thực hiện",
  hoan_thanh: "Hoàn thành",
  da_huy: "Đã hủy",
};

export function RequestScreen() {
  const { workspace, notify } = useWorkspace();
  const [productId, setProductId] = useState("mountain");
  const [quantity, setQuantity] = useState(10);
  const [assigneeId, setAssigneeId] = useState("employee-nam");
  const [created, setCreated] = useState<ProductionRequest | null>(null);
  const [preview, setPreview] = useState<RequestPreview | null>(null);
  const [tab, setTab] = useState<"bike" | "wheel">("bike");
  const form = useRef<HTMLFormElement>(null);
  const create = useWorkspaceMutation((api, input: RequestInput) => api.createRequest(input));
  const update = useWorkspaceMutation((api, input: { id: string; input: RequestInput }) =>
    api.updateRequest(input),
  );
  const calculate = useWorkspaceMutation((api, id: string) => api.previewRequest(id));
  const send = useWorkspaceMutation((api, input: { id: string; token: string }) =>
    api.sendRequest(input),
  );
  const products = workspace.items.filter((item) => item.kind === "thanh_pham" && item.active);
  const employees = workspace.employees.filter(
    (employee) => employee.active && employee.role === "nhan_vien",
  );
  const product = itemById(workspace.items, productId);
  const validQuantity = Number.isSafeInteger(quantity) && quantity > 0 ? quantity : 0;
  const record = workspace.requests.find((entry) => entry.id === created?.id) ?? created;
  const locked = !!record && record.status !== "nhap";
  const busy = create.isPending || update.isPending || calculate.isPending || send.isPending;
  let plan: ProductionPlan | null = null;
  let planError: Error | null = null;
  try {
    plan =
      locked && record
        ? record.plan
        : (preview?.plan ??
          calculatePlan(workspace.items, productId, validQuantity, workspace.boms));
  } catch (error) {
    planError = error instanceof Error ? error : new Error("Không thể tính kế hoạch.");
  }
  const productBom = workspace.boms.find((bom) => bom.id === plan?.bikeBomId);
  const wheelBom = workspace.boms.find((bom) => bom.id === plan?.wheelBomId);
  const shortages = plan
    ? [
        ...plan.bikeMaterials.filter((line) => line.itemId !== "wheel"),
        ...plan.wheelMaterials,
      ].filter((line) => line.missing > 0)
    : [];

  async function submit() {
    try {
      const input = { productId, quantity, assigneeId: assigneeId || null };
      const result = record
        ? await update.mutateAsync({ id: record.id, input })
        : await create.mutateAsync(input);
      setCreated(result);
      setPreview(null);
      notify(`Đã lưu nháp ${result.code}`, "Tính kế hoạch trước khi gửi. Tồn kho không thay đổi.");
    } catch {
      /* The request error remains visible in the action section. */
    }
  }

  async function refresh() {
    if (!record || !form.current?.reportValidity()) return;
    try {
      const result = await calculate.mutateAsync(record.id);
      setPreview(result);
      notify(
        "Đã tính kế hoạch nháp",
        "Kế hoạch có hiệu lực 10 phút trong phiên demo. Gửi để lưu cây lệnh.",
      );
    } catch {
      setPreview(null);
    }
  }

  async function sendRequest() {
    if (!record || !preview) return;
    try {
      const result = await send.mutateAsync({ id: record.id, token: preview.token });
      setCreated(result);
      setPreview(null);
      notify(
        `Đã gửi ${result.code}`,
        "Cây lệnh nháp được tạo từ kế hoạch; chưa ghi tăng hoặc giảm tồn kho.",
      );
    } catch {
      setPreview(null);
    }
  }

  function invalidatePreview() {
    setPreview(null);
    calculate.reset();
    send.reset();
  }

  const draftChanged =
    !!record &&
    (record.productId !== productId ||
      record.quantity !== quantity ||
      record.assigneeId !== (assigneeId || null));
  const statusLabel = requestLabels[record?.status ?? "nhap"];

  return (
    <>
      <PageTitle
        step="02 / 04"
        title="Yêu cầu thành phẩm"
        description="Từ nhu cầu giao xe đến kế hoạch vật tư cần chuẩn bị."
        action={
          created ? (
            <ActionButton
              disabled={busy}
              onClick={() => {
                setCreated(null);
                setPreview(null);
                create.reset();
                update.reset();
                calculate.reset();
                send.reset();
              }}
            >
              <FilePlus2 size={16} />
              Yêu cầu mới
            </ActionButton>
          ) : undefined
        }
      />
      <div className="m-work-grid">
        <form
          ref={form}
          className="m-main-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <Panel
            title="Thông tin yêu cầu"
            subtitle="Ưu tiên thành phẩm có sẵn, chỉ sản xuất phần còn thiếu."
            action={
              <Status tone="neutral">
                {record ? `${record.code} · ${statusLabel}` : "Chưa lưu"}
              </Status>
            }
          >
            <fieldset className="m-panel-body m-fields" disabled={locked || busy}>
              <Field label="Model thành phẩm" required>
                <select
                  value={productId}
                  onChange={(event) => {
                    setProductId(event.target.value);
                    invalidatePreview();
                  }}
                >
                  {products.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.code} · {item.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Số lượng cần đáp ứng" required hint="Đơn vị: xe">
                <input
                  type="number"
                  min={1}
                  max={1000000}
                  step={1}
                  required
                  value={Number.isNaN(quantity) ? "" : quantity}
                  onChange={(event) => {
                    setQuantity(event.target.valueAsNumber);
                    invalidatePreview();
                  }}
                />
              </Field>
              <Field
                label="Nhân viên được giao"
                hint="Có thể để trống khi lưu nháp; bắt buộc khi gửi."
              >
                <select
                  value={assigneeId}
                  onChange={(event) => {
                    setAssigneeId(event.target.value);
                    invalidatePreview();
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
              <Field label="Người lập yêu cầu">
                <input value={`${currentManager.code} · ${currentManager.name}`} readOnly />
              </Field>
              <Field label={locked ? "BOM thành phẩm đã chốt" : "BOM thành phẩm đang áp dụng"}>
                <input
                  value={
                    productBom
                      ? `${product.code} · Phiên bản ${productBom.version}`
                      : plan
                        ? "Không cần sản xuất thành phẩm"
                        : "Chưa có BOM hiện hành"
                  }
                  readOnly
                />
              </Field>
              <Field label="Trạng thái">
                <input value={statusLabel} readOnly />
              </Field>
              {record && (
                <Field label="Ngày tạo yêu cầu" wide>
                  <input value={new Date(record.createdAt).toLocaleString("vi-VN")} readOnly />
                </Field>
              )}
            </fieldset>
          </Panel>
          <Panel
            title="Nhu cầu sản xuất"
            subtitle={
              locked
                ? "Kế hoạch đã lưu khi gửi; không tự tính lại theo tồn hoặc BOM mới."
                : preview
                  ? "Ảnh chụp kế hoạch của yêu cầu đã lưu nháp, có hiệu lực 10 phút."
                  : `Ước tính theo tồn mặt hàng ${product.name}. Lưu nháp để tính kế hoạch gửi.`
            }
            action={
              <span className="m-icon-label">
                <GitBranch size={15} />
                {productBom
                  ? `BOM v${productBom.version}`
                  : plan
                    ? "Dùng tồn thành phẩm"
                    : "Chưa có BOM"}
                {wheelBom ? ` / v${wheelBom.version}` : ""}
              </span>
            }
          >
            {plan ? (
              <>
                <div className="m-metric-strip">
                  <div>
                    <span>Cần đáp ứng</span>
                    <strong>
                      {number(plan.requested)}
                      <small> xe</small>
                    </strong>
                  </div>
                  <div>
                    <span>Dùng tồn thành phẩm</span>
                    <strong>
                      {number(plan.useProducts)}
                      <small> xe</small>
                    </strong>
                  </div>
                  <div className="m-metric-highlight">
                    <span>Cần sản xuất thêm</span>
                    <strong>
                      {number(plan.bikesToMake)}
                      <small> xe</small>
                    </strong>
                  </div>
                </div>
                <div
                  className="m-inline-tabs"
                  role="tablist"
                  aria-label="Cấp BOM"
                  onKeyDown={(event) => {
                    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
                    event.preventDefault();
                    const next = tab === "bike" ? "wheel" : "bike";
                    setTab(next);
                    document.getElementById(`${next}-plan-tab`)?.focus();
                  }}
                >
                  <button
                    type="button"
                    role="tab"
                    id="bike-plan-tab"
                    tabIndex={tab === "bike" ? 0 : -1}
                    aria-selected={tab === "bike"}
                    aria-controls="demand-panel"
                    onClick={() => setTab("bike")}
                  >
                    Cấp 1 · Lắp xe <span>{number(plan.bikesToMake)} xe</span>
                  </button>
                  <button
                    type="button"
                    role="tab"
                    id="wheel-plan-tab"
                    tabIndex={tab === "wheel" ? 0 : -1}
                    aria-selected={tab === "wheel"}
                    aria-controls="demand-panel"
                    onClick={() => setTab("wheel")}
                  >
                    Cấp 2 · Cụm bánh <span>{number(plan.wheelsToMake)} cụm</span>
                  </button>
                </div>
                <div
                  id="demand-panel"
                  role="tabpanel"
                  aria-labelledby={tab === "bike" ? "bike-plan-tab" : "wheel-plan-tab"}
                >
                  <MaterialTable
                    items={workspace.items}
                    lines={tab === "bike" ? plan.bikeMaterials : plan.wheelMaterials}
                  />
                </div>
                <div className="m-panel-body">
                  <Notice tone={shortages.length ? "amber" : "green"}>
                    {locked
                      ? `Kế hoạch đã lưu khi gửi. Yêu cầu hiện ở trạng thái ${statusLabel.toLocaleLowerCase("vi-VN")}; tồn chỉ thay đổi khi ghi sổ chứng từ kho.`
                      : shortages.length
                        ? `Có ${shortages.length} loại vật tư cần bổ sung. Anh vẫn có thể ghi nhận yêu cầu và lên kế hoạch sản xuất.`
                        : "Vật tư mẫu đáp ứng phần nhu cầu đã tính. Tồn kho sẽ được kiểm tra lại khi duyệt xuất."}
                  </Notice>
                </div>
              </>
            ) : (
              <div className="m-panel-body">
                <Notice tone="amber">
                  {planError?.message ?? "Chưa có kế hoạch đã lưu."} Anh vẫn có thể lưu nháp yêu
                  cầu; bổ sung BOM trước khi tính và gửi kế hoạch.
                </Notice>
              </div>
            )}
            <FormError error={create.error ?? update.error ?? calculate.error ?? send.error} />
            {created && (
              <div className="m-success-card">
                <Check size={20} />
                <div>
                  <strong>
                    {record?.code} · {statusLabel}
                  </strong>
                  <p>
                    {plan
                      ? `${number(plan.bikesToMake)} xe cần lắp · ${number(plan.wheelsToMake)} cụm bánh cần sản xuất`
                      : "Đã lưu nháp. Chưa có kế hoạch để gửi."}
                  </p>
                </div>
                {locked && (
                  <Link className="m-text-link" to={`/quan-ly/lenh-san-xuat?request=${created.id}`}>
                    Xem cây lệnh
                    <ArrowRight size={16} />
                  </Link>
                )}
              </div>
            )}
            <footer className="m-action-bar">
              <span>Yêu cầu không làm thay đổi tồn kho.</span>
              <div>
                <ActionButton
                  onClick={() => void refresh()}
                  disabled={!record || locked || busy || draftChanged}
                >
                  <RefreshCw size={15} className={calculate.isPending ? "m-spinning" : ""} />
                  Tính kế hoạch
                </ActionButton>
                <ActionButton type="submit" disabled={locked || busy || !validQuantity}>
                  {create.isPending || update.isPending ? "Đang lưu…" : "Lưu nháp"}
                </ActionButton>
                <ActionButton
                  variant="primary"
                  onClick={() => void sendRequest()}
                  disabled={locked || busy || !preview || draftChanged || !assigneeId}
                >
                  {send.isPending ? "Đang gửi…" : "Gửi yêu cầu"}
                  <ArrowRight size={16} />
                </ActionButton>
              </div>
            </footer>
          </Panel>
        </form>
        <aside className="m-side-stack">
          {plan ? (
            <Panel title="Từ nhu cầu đến vật tư">
              <div className="m-panel-body m-bom-flow">
                <div className="m-flow-product">
                  <Bike size={28} strokeWidth={1.4} />
                  <div>
                    <small>{product.code}</small>
                    <strong>{product.name}</strong>
                  </div>
                </div>
                <div className="m-flow-node">
                  <span>Nhu cầu thành phẩm</span>
                  <strong>
                    {number(plan.requested)} <small>xe</small>
                  </strong>
                </div>
                <ArrowDown className="m-flow-arrow" size={17} />
                <div className="m-flow-split">
                  <div>
                    <span>Có thể dùng ngay</span>
                    <strong>
                      {number(plan.useProducts)} <small>xe</small>
                    </strong>
                  </div>
                  <div>
                    <span>Cần lắp thêm</span>
                    <strong>
                      {number(plan.bikesToMake)} <small>xe</small>
                    </strong>
                  </div>
                </div>
                <div className="m-flow-connector" />
                <div className="m-flow-node">
                  <span>Cụm bánh cần cho xe</span>
                  <strong>
                    {number(plan.wheelsRequired)} <small>cụm</small>
                  </strong>
                </div>
                <div className="m-formula">
                  <span>{number(plan.wheelsRequired)} cần dùng</span>
                  <span>−</span>
                  <span>{number(plan.useWheels)} có sẵn</span>
                </div>
                <div className="m-flow-answer">
                  <span>Cần sản xuất cụm bánh</span>
                  <strong>
                    {number(plan.wheelsToMake)}
                    <small> cụm</small>
                  </strong>
                </div>
                <div className="m-bom-components">
                  {plan.wheelMaterials.map((line) => (
                    <div key={line.itemId}>
                      <span>{itemById(workspace.items, line.itemId).name}</span>
                      <strong>{number(line.required)}</strong>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>
          ) : (
            <Panel title="Chờ định mức sản xuất">
              <div className="m-panel-body">
                <Notice tone="amber">
                  Cần BOM hiện hành cho mặt hàng phải sản xuất. Không phân rã hoặc tự đặt định mức
                  thay thế.
                </Notice>
              </div>
            </Panel>
          )}
          <div className="m-rule-note">
            <Package size={20} strokeWidth={1.5} />
            <strong>Phần thiếu được tính hai cấp</strong>
            <p>
              Dùng tồn xe trước, sau đó dùng tồn cụm bánh. Chỉ phân rã BOM cho số cụm bánh còn
              thiếu.
            </p>
          </div>
        </aside>
      </div>
    </>
  );
}
