import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
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
import { employees } from "./types";
import type { ProductionRequest, RequestInput } from "./types";
import { useWorkspace, useWorkspaceMutation } from "./workspace-hooks";

export function RequestScreen() {
  const { workspace, notify, queryKey } = useWorkspace();
  const queryClient = useQueryClient();
  const [productId, setProductId] = useState("mountain");
  const [quantity, setQuantity] = useState(10);
  const [reference, setReference] = useState("");
  const [assignee, setAssignee] = useState<string>("Lê Hoàng Nam");
  const [note, setNote] = useState("");
  const [created, setCreated] = useState<ProductionRequest | null>(null);
  const [tab, setTab] = useState<"bike" | "wheel">("bike");
  const [refreshing, setRefreshing] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  const create = useWorkspaceMutation((api, input: RequestInput) => api.createRequest(input));
  const products = workspace.items.filter((item) => item.kind === "product");
  const product = itemById(workspace.items, productId);
  const validQuantity = Number.isSafeInteger(quantity) && quantity > 0 ? quantity : 0;
  const plan = created?.plan ?? calculatePlan(workspace.items, productId, validQuantity);
  const shortages = [
    ...plan.bikeMaterials.filter((line) => line.itemId !== "wheel"),
    ...plan.wheelMaterials,
  ].filter((line) => line.missing > 0);

  async function submit() {
    try {
      const result = await create.mutateAsync({ productId, quantity, reference, assignee, note });
      setCreated(result);
      notify(`Đã tạo ${result.code}`, "Yêu cầu đã được ghi nhận. Tồn kho không thay đổi.");
    } catch {
      /* The request error remains visible in the action section. */
    }
  }

  async function refresh() {
    if (!form.current?.reportValidity()) return;
    setRefreshing(true);
    try {
      await queryClient.invalidateQueries({ queryKey });
      notify("Đã tính lại nhu cầu", "Sử dụng số tồn mới nhất trong phiên demo này.");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <>
      <PageTitle
        step="02 / 04"
        title="Yêu cầu thành phẩm"
        description="Từ nhu cầu giao xe đến kế hoạch vật tư cần chuẩn bị."
        action={
          created ? (
            <ActionButton
              onClick={() => {
                setCreated(null);
                create.reset();
                setReference("");
                setNote("");
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
              <Status tone={created ? "green" : "neutral"}>
                {created ? created.code : "Chưa tạo"}
              </Status>
            }
          >
            <fieldset className="m-panel-body m-fields" disabled={!!created || create.isPending}>
              <Field label="Model thành phẩm" required>
                <select value={productId} onChange={(event) => setProductId(event.target.value)}>
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
                  onChange={(event) => setQuantity(event.target.valueAsNumber)}
                />
              </Field>
              <Field label="Người phụ trách" required>
                <select value={assignee} onChange={(event) => setAssignee(event.target.value)}>
                  {employees.map((name) => (
                    <option key={name}>{name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Mã đơn bên ngoài" hint="Thông tin tham chiếu, không đồng bộ đơn hàng">
                <input
                  value={reference}
                  placeholder="Ví dụ: DH-2026-251"
                  onChange={(event) => setReference(event.target.value)}
                />
              </Field>
              <Field label="Ghi chú yêu cầu" wide>
                <textarea
                  rows={2}
                  placeholder="Yêu cầu về đợt giao hoặc lưu ý sản xuất…"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
              </Field>
            </fieldset>
          </Panel>
          <Panel
            title="Nhu cầu sản xuất"
            subtitle={`Tính theo tồn kho hiện tại của ${product.name}.`}
            action={
              <span className="m-icon-label">
                <GitBranch size={15} />
                BOM 2 cấp
              </span>
            }
          >
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
                {shortages.length
                  ? `Có ${shortages.length} loại vật tư cần bổ sung. Anh vẫn có thể ghi nhận yêu cầu và lên kế hoạch sản xuất.`
                  : "Vật tư mẫu đáp ứng phần nhu cầu đã tính. Tồn kho sẽ được kiểm tra lại khi duyệt xuất."}
              </Notice>
            </div>
            <FormError error={create.error} />
            {created && (
              <div className="m-success-card">
                <Check size={20} />
                <div>
                  <strong>{created.code} đã được ghi nhận</strong>
                  <p>
                    {number(plan.bikesToMake)} xe cần lắp · {number(plan.wheelsToMake)} cụm bánh cần
                    sản xuất
                  </p>
                </div>
                <Link className="m-text-link" to={`/quan-ly/lenh-san-xuat?request=${created.id}`}>
                  Tạo lệnh
                  <ArrowRight size={16} />
                </Link>
              </div>
            )}
            <footer className="m-action-bar">
              <span>Yêu cầu không làm thay đổi tồn kho.</span>
              <div>
                <ActionButton
                  onClick={() => void refresh()}
                  disabled={!!created || create.isPending || refreshing}
                >
                  <RefreshCw size={15} className={refreshing ? "m-spinning" : ""} />
                  Tính lại nhu cầu
                </ActionButton>
                <ActionButton
                  type="submit"
                  variant="primary"
                  disabled={!!created || create.isPending || !validQuantity}
                >
                  {create.isPending ? "Đang tạo…" : "Tạo yêu cầu"}
                  <ArrowRight size={16} />
                </ActionButton>
              </div>
            </footer>
          </Panel>
        </form>
        <aside className="m-side-stack">
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
