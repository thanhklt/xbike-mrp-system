import { useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  ClipboardCheck,
  FilePlus2,
  Plus,
  Save,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import {
  ActionButton,
  ConfirmDialog,
  Field,
  FormError,
  Notice,
  PageTitle,
  Panel,
  Status,
} from "./components";
import { documentTotal, itemById, money, number, today } from "./planning";
import { currentManager } from "./types";
import type { DocumentLine, Receipt, ReceiptInput } from "./types";
import { useWorkspace, useWorkspaceMutation } from "./workspace-hooks";

interface ReceiptRow extends DocumentLine {
  rowId: string;
}
const startingRows = (): ReceiptRow[] => [
  { rowId: crypto.randomUUID(), itemId: "frame", quantity: 20, price: 450000 },
  { rowId: crypto.randomUUID(), itemId: "rim", quantity: 12, price: 180000 },
];

export function ReceivingScreen() {
  const { workspace, notify } = useWorkspace();
  const last = workspace.receipts[workspace.receipts.length - 1];
  const [record, setRecord] = useState<Receipt | undefined>(last);
  const [date, setDate] = useState(last?.date ?? today());
  const [supplierId, setSupplierId] = useState(last?.supplierId ?? workspace.suppliers[0].id);
  const [note, setNote] = useState(last?.note ?? "");
  const [rows, setRows] = useState<ReceiptRow[]>(() =>
    last ? last.lines.map((line) => ({ ...line, rowId: crypto.randomUUID() })) : startingRows(),
  );
  const [confirmOpen, setConfirmOpen] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  const save = useWorkspaceMutation((api, input: ReceiptInput) => api.saveReceipt(input));
  const confirm = useWorkspaceMutation((api, input: ReceiptInput) => api.confirmReceipt(input));
  const materials = workspace.items.filter(
    (item) => item.active && (item.kind === "nguyen_vat_lieu" || item.kind === "linh_kien"),
  );
  const supplier = workspace.suppliers.find((entry) => entry.id === supplierId);
  const creator =
    workspace.employees.find((entry) => entry.id === record?.creatorId) ?? currentManager;
  const locked = record?.status === "hoan_thanh";
  const busy = save.isPending || confirm.isPending;
  const total = documentTotal(rows);
  const quantity = rows.reduce(
    (sum, row) => sum + (Number.isFinite(row.quantity) ? row.quantity : 0),
    0,
  );

  function updateRow(rowId: string, changes: Partial<DocumentLine>) {
    save.reset();
    confirm.reset();
    setRows((previous) =>
      previous.map((row) => (row.rowId === rowId ? { ...row, ...changes } : row)),
    );
  }

  function input(): ReceiptInput {
    return {
      id: record?.id,
      date,
      supplierId,
      note,
      lines: rows.map(({ itemId, quantity, price }) => ({ itemId, quantity, price })),
    };
  }

  function newReceipt() {
    setRecord(undefined);
    setRows(startingRows());
    setDate(today());
    setNote("");
    save.reset();
    confirm.reset();
  }

  async function saveDraft() {
    try {
      const result = await save.mutateAsync(input());
      setRecord(result);
      notify(
        `Đã lưu nháp ${result.code}`,
        "Tồn kho chưa thay đổi. Anh có thể tiếp tục chỉnh sửa phiếu.",
      );
    } catch {
      /* Mutation error is shown beside the form. */
    }
  }

  async function confirmReceipt() {
    try {
      const result = await confirm.mutateAsync(input());
      setRecord(result);
      setConfirmOpen(false);
      notify(
        `Đã xác nhận ${result.code}`,
        `${number(quantity)} đơn vị vật tư đã được cộng vào tồn kho demo.`,
      );
    } catch {
      setConfirmOpen(false);
    }
  }

  return (
    <>
      <PageTitle
        step="01 / 04"
        title="Phiếu nhập kho"
        description="Tiếp nhận nguyên vật liệu, linh kiện từ nhà cung cấp."
        action={
          <ActionButton onClick={newReceipt} disabled={busy}>
            <FilePlus2 size={16} />
            Phiếu mới
          </ActionButton>
        }
      />
      <div className="m-document-bar">
        <div>
          <span className="m-document-code">{record?.code ?? "Phiếu nhập mới"}</span>
          <Status tone={locked ? "green" : "neutral"}>{locked ? "Đã nhập kho" : "Bản nháp"}</Status>
        </div>
        <div className="m-document-steps">
          <span className="is-current">
            <Check size={13} />
            Thông tin phiếu
          </span>
          <span className="m-step-rule" />
          <span className={locked ? "is-current" : ""}>
            <ClipboardCheck size={14} />
            Xác nhận nhập kho
          </span>
        </div>
      </div>
      <div className="m-work-grid">
        <form
          ref={form}
          className="m-main-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void saveDraft();
          }}
        >
          <Panel title="Thông tin phiếu" subtitle="Thông tin nguồn nhập và người tiếp nhận.">
            <fieldset disabled={locked || busy} className="m-panel-body m-fields">
              <Field label="Nhà cung cấp" required wide>
                <select
                  value={supplierId}
                  onChange={(event) => setSupplierId(event.target.value)}
                  required
                >
                  {workspace.suppliers.map((entry) => (
                    <option key={entry.id} value={entry.id}>
                      {entry.code} · {entry.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Ngày nhập" required>
                <input
                  type="date"
                  required
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                />
              </Field>
              <Field label="Người lập">
                <input value={`${creator.code} · ${creator.name}`} readOnly />
              </Field>
              <Field label="Ngày tạo phiếu" hint="Độc lập với ngày nhập nghiệp vụ">
                <input
                  value={
                    record
                      ? new Date(record.createdAt).toLocaleString("vi-VN")
                      : "Được ghi khi lưu phiếu"
                  }
                  readOnly
                />
              </Field>
              <Field label="Ghi chú" wide>
                <textarea
                  rows={2}
                  placeholder="Ví dụ: Nhập bổ sung linh kiện cho đợt lắp xe đầu tháng…"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
              </Field>
            </fieldset>
          </Panel>
          <Panel
            title="Nguyên vật liệu và linh kiện"
            subtitle="Mỗi vật tư chỉ xuất hiện một lần trong phiếu."
            action={<span className="m-subtle-count">{rows.length} dòng vật tư</span>}
          >
            <fieldset disabled={locked || busy}>
              <div className="m-table-scroll">
                <table className="m-table m-receipt-table">
                  <thead>
                    <tr>
                      <th>Nguyên vật liệu</th>
                      <th className="m-number">Tồn kho</th>
                      <th className="m-number">Số lượng nhập</th>
                      <th className="m-number">Đơn giá (₫)</th>
                      <th className="m-number">Thành tiền</th>
                      <th>
                        <span className="m-sr-only">Thao tác</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => {
                      const item = itemById(workspace.items, row.itemId);
                      return (
                        <tr key={row.rowId}>
                          <td>
                            <select
                              aria-label={`Nguyên vật liệu ${item.code}`}
                              value={row.itemId}
                              onChange={(event) => {
                                const next = itemById(workspace.items, event.target.value);
                                updateRow(row.rowId, { itemId: next.id, price: next.price });
                              }}
                            >
                              {materials.map((option) => (
                                <option
                                  key={option.id}
                                  value={option.id}
                                  disabled={rows.some(
                                    (entry) =>
                                      entry.rowId !== row.rowId && entry.itemId === option.id,
                                  )}
                                >
                                  {option.name}
                                </option>
                              ))}
                            </select>
                            <small>
                              {item.code}{" "}
                              <span>
                                · SKU {item.sku} · {item.unit}
                              </span>
                            </small>
                          </td>
                          <td className="m-number m-muted">{number(item.stock)}</td>
                          <td className="m-number">
                            <input
                              aria-label={`Số lượng nhập ${item.name}`}
                              type="number"
                              min={1}
                              max={1000000}
                              step={1}
                              required
                              value={Number.isNaN(row.quantity) ? "" : row.quantity}
                              onChange={(event) =>
                                updateRow(row.rowId, { quantity: event.target.valueAsNumber })
                              }
                            />
                          </td>
                          <td className="m-number">
                            <input
                              aria-label={`Đơn giá ${item.name}`}
                              type="number"
                              min={0}
                              max={1000000000}
                              step={1}
                              required
                              value={Number.isNaN(row.price) ? "" : row.price}
                              onChange={(event) =>
                                updateRow(row.rowId, { price: event.target.valueAsNumber })
                              }
                            />
                          </td>
                          <td className="m-number">
                            <strong>
                              {Number.isFinite(row.quantity * row.price)
                                ? money(row.quantity * row.price)
                                : "—"}
                            </strong>
                          </td>
                          <td>
                            <ActionButton
                              variant="plain"
                              aria-label={`Xóa ${item.name}`}
                              disabled={rows.length === 1 || locked || busy}
                              onClick={() =>
                                setRows((previous) =>
                                  previous.filter((entry) => entry.rowId !== row.rowId),
                                )
                              }
                            >
                              <Trash2 size={16} />
                            </ActionButton>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="m-table-add">
                <ActionButton
                  variant="plain"
                  disabled={rows.length === materials.length || locked || busy}
                  onClick={() => {
                    const next = materials.find(
                      (item) => !rows.some((row) => row.itemId === item.id),
                    );
                    if (next)
                      setRows((previous) => [
                        ...previous,
                        {
                          rowId: crypto.randomUUID(),
                          itemId: next.id,
                          quantity: 1,
                          price: next.price,
                        },
                      ]);
                  }}
                >
                  <Plus size={16} />
                  Thêm nguyên vật liệu
                </ActionButton>
              </div>
            </fieldset>
            <div className="m-panel-total">
              <span>Tổng giá trị phiếu</span>
              <strong>{Number.isFinite(total) ? money(total) : "—"}</strong>
            </div>
            <div className="m-panel-body m-receipt-bottom">
              <FormError error={save.error ?? confirm.error} />
              <Notice tone={locked ? "green" : "neutral"}>
                {locked
                  ? "Phiếu đã nhập kho và được khóa. Số tồn trước/sau xác nhận được lưu để đối chiếu."
                  : "Lưu nháp không làm thay đổi tồn kho. Chỉ xác nhận nhập mới ghi tăng số lượng."}
              </Notice>
            </div>
            <footer className="m-action-bar">
              <span>
                <ShieldCheck size={16} />
                {locked ? "Đã hoàn tất nhập kho" : "Kiểm tra phiếu trước khi xác nhận"}
              </span>
              <div>
                <ActionButton type="submit" disabled={locked || busy}>
                  <Save size={16} />
                  {save.isPending ? "Đang lưu…" : "Lưu nháp"}
                </ActionButton>
                <ActionButton
                  variant="primary"
                  disabled={locked || busy}
                  onClick={() => {
                    if (form.current?.reportValidity()) setConfirmOpen(true);
                  }}
                >
                  Xác nhận nhập kho
                  <ArrowRight size={16} />
                </ActionButton>
              </div>
            </footer>
          </Panel>
        </form>
        <aside className="m-side-stack">
          <Panel title="Tóm tắt phiếu nhập">
            <div className="m-panel-body">
              <div className="m-summary-lead">
                <span>Giá trị nhập kho</span>
                <strong>{Number.isFinite(total) ? money(total) : "—"}</strong>
              </div>
              <dl className="m-summary-list">
                <div>
                  <dt>Loại chứng từ</dt>
                  <dd>Nhập vật tư từ nhà cung cấp</dd>
                </div>
                <div>
                  <dt>Số dòng vật tư</dt>
                  <dd>{rows.length}</dd>
                </div>
                <div>
                  <dt>Tổng số lượng</dt>
                  <dd>{number(quantity)}</dd>
                </div>
              </dl>
              <div className="m-summary-divider" />
              <div className="m-stock-heading">
                {locked ? "Tồn trước / sau xác nhận" : "Dự kiến tồn sau nhập"}
              </div>
              {rows.map((row) => {
                const item = itemById(workspace.items, row.itemId);
                const posting = record?.posting?.find((entry) => entry.itemId === item.id);
                return (
                  <div className="m-stock-preview" key={row.rowId}>
                    <span>{item.name}</span>
                    <div>
                      <span>{number(posting?.before ?? item.stock)}</span>
                      <ArrowRight size={12} />
                      <strong>
                        {Number.isFinite(row.quantity)
                          ? number(posting?.after ?? item.stock + row.quantity)
                          : "—"}
                      </strong>
                    </div>
                  </div>
                );
              })}
            </div>
          </Panel>
          <div className="m-rule-note">
            <ShieldCheck size={20} strokeWidth={1.5} />
            <strong>Nhập đúng, tồn chính xác</strong>
            <p>
              Kiểm đếm vật tư thực nhận trước khi xác nhận. Phiếu đã hoàn tất được giữ lại để đối
              chiếu.
            </p>
          </div>
        </aside>
      </div>
      {confirmOpen && (
        <ConfirmDialog
          title="Xác nhận nhập kho?"
          confirmLabel="Xác nhận nhập kho"
          busy={confirm.isPending}
          onClose={() => setConfirmOpen(false)}
          onConfirm={() => void confirmReceipt()}
        >
          <p>
            Nhập <strong>{number(quantity)} đơn vị</strong> thuộc{" "}
            <strong>{rows.length} dòng vật tư</strong> từ {supplier?.name}.
          </p>
          <div className="m-dialog-stat">
            <span>Tổng giá trị</span>
            <strong>{money(total)}</strong>
          </div>
          <Notice>Sau xác nhận, phiếu được khóa và tồn kho demo được cộng đúng một lần.</Notice>
        </ConfirmDialog>
      )}
    </>
  );
}
