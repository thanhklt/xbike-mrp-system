import { useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Search,
  ShieldCheck,
  X,
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
import { documentTotal, itemById, issueApprovalProblem, money, number } from "./planning";
import type { IssueKind, Issue, IssueStatus } from "./types";
import { useWorkspace, useWorkspaceMutation } from "./workspace-hooks";

const statusNames: Record<IssueStatus, string> = {
  cho_duyet: "Chờ duyệt",
  da_duyet: "Đã duyệt",
  tu_choi: "Từ chối",
};
const kindNames: Record<IssueKind, string> = {
  xuat_vat_tu: "Xuất vật tư",
  xuat_thanh_pham: "Xuất thành phẩm",
};
const statusTones = { cho_duyet: "amber", da_duyet: "green", tu_choi: "red" } as const;

export function ApprovalScreen() {
  const { workspace, notify } = useWorkspace();
  const [selectedId, setSelectedId] = useState("issue-26");
  const [filter, setFilter] = useState<"all" | IssueStatus>("cho_duyet");
  const [kind, setKind] = useState<"all" | IssueKind>("all");
  const [search, setSearch] = useState("");
  const [reason, setReason] = useState("");
  const [dialog, setDialog] = useState<"approve" | "reject" | null>(null);
  const [mobileDetail, setMobileDetail] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const approve = useWorkspaceMutation((api, id: string) => api.approveIssue(id));
  const reject = useWorkspaceMutation((api, input: { id: string; reason: string }) =>
    api.rejectIssue(input),
  );
  const pending = workspace.issues.filter((issue) => issue.status === "cho_duyet");
  const blocked = pending.filter((issue) => issueApprovalProblem(workspace, issue));
  const creatorName = (issue: Issue) => {
    const employee = workspace.employees.find((entry) => entry.id === issue.creatorId);
    return employee ? `${employee.code} · ${employee.name}` : "Không có thông tin người lập";
  };
  const sourceName = (issue: Issue) => {
    if (issue.kind === "xuat_vat_tu") {
      const order = workspace.orders.find((entry) => entry.id === issue.orderId);
      return order
        ? `${order.code} · ${itemById(workspace.items, order.outputId).name}`
        : "Không tìm thấy lệnh nguồn";
    }
    const request = workspace.requests.find((entry) => entry.id === issue.requestId);
    return request
      ? `${request.code} · ${itemById(workspace.items, request.productId).name}`
      : "Không tìm thấy yêu cầu nguồn";
  };
  const filtered = workspace.issues.filter((issue) => {
    const searchable = [
      issue.code,
      creatorName(issue),
      sourceName(issue),
      ...issue.lines.map((line) => itemById(workspace.items, line.itemId).name),
    ]
      .join(" ")
      .toLocaleLowerCase("vi");
    return (
      (filter === "all" || issue.status === filter) &&
      (kind === "all" || issue.kind === kind) &&
      searchable.includes(search.trim().toLocaleLowerCase("vi"))
    );
  });
  const selected = filtered.find((issue) => issue.id === selectedId) ?? filtered[0];
  const selectedProblem =
    selected?.status === "cho_duyet" ? issueApprovalProblem(workspace, selected) : null;
  const selectedTotal = selected ? documentTotal(selected.lines) : null;
  const busy = approve.isPending || reject.isPending;

  function select(issue: Issue) {
    setSelectedId(issue.id);
    setReason("");
    approve.reset();
    reject.reset();
    setMobileDetail(true);
    window.requestAnimationFrame(() => heading.current?.focus({ preventScroll: true }));
  }

  async function submit() {
    if (!selected) return;
    try {
      if (dialog === "approve") {
        await approve.mutateAsync(selected.id);
        notify(
          `Đã duyệt ${selected.code}`,
          "Tồn kho demo đã được trừ một lần theo số lượng trên phiếu.",
        );
        setFilter("all");
      } else {
        await reject.mutateAsync({ id: selected.id, reason });
        notify(`Đã từ chối ${selected.code}`, "Lý do được lưu trên phiếu. Tồn kho giữ nguyên.");
        setFilter("all");
      }
      setDialog(null);
    } catch {
      /* Keep the error visible, including in the open confirmation. */
    }
  }

  return (
    <>
      <PageTitle
        step="04 / 04"
        title="Duyệt phiếu xuất"
        description={`${pending.length} phiếu chờ duyệt · ${blocked.length} phiếu chưa đủ điều kiện xuất kho.`}
      />
      <div className={`m-approval-grid ${mobileDetail ? "is-detail" : "is-list"}`}>
        <section className="m-approval-list m-panel" aria-label="Danh sách phiếu xuất">
          <header className="m-panel-heading">
            <div>
              <h2>Hàng chờ phê duyệt</h2>
              <p>Quản lý lập và xử lý phiếu xuất</p>
            </div>
            <span className="m-nav-count">{pending.length}</span>
          </header>
          <div className="m-queue-controls">
            <label className="m-search">
              <Search size={17} aria-hidden="true" />
              <input
                aria-label="Tìm phiếu xuất"
                placeholder="Tìm mã phiếu, vật tư, nhân viên…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              {search && (
                <button aria-label="Xóa tìm kiếm" onClick={() => setSearch("")}>
                  <X size={14} />
                </button>
              )}
            </label>
            <div className="m-queue-filter">
              <label>
                <span className="m-sr-only">Trạng thái phiếu xuất</span>
                <select
                  value={filter}
                  onChange={(event) => setFilter(event.target.value as typeof filter)}
                >
                  <option value="all">Tất cả trạng thái</option>
                  <option value="cho_duyet">Chờ duyệt ({pending.length})</option>
                  <option value="da_duyet">Đã duyệt</option>
                  <option value="tu_choi">Từ chối</option>
                </select>
              </label>
              <label>
                <span className="m-sr-only">Loại phiếu xuất</span>
                <select
                  value={kind}
                  onChange={(event) => setKind(event.target.value as typeof kind)}
                >
                  <option value="all">Tất cả loại phiếu</option>
                  {Object.entries(kindNames).map(([value, name]) => (
                    <option key={value} value={value}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
          <div className="m-queue-items">
            {filtered.length ? (
              filtered.map((issue) => {
                const problem =
                  issue.status === "cho_duyet" ? issueApprovalProblem(workspace, issue) : null;
                return (
                  <button
                    className={`m-queue-item ${selected?.id === issue.id ? "is-selected" : ""}`}
                    key={issue.id}
                    onClick={() => select(issue)}
                    aria-pressed={selected?.id === issue.id}
                  >
                    <div className="m-queue-item-top">
                      <strong>{issue.code}</strong>
                      <Status tone={statusTones[issue.status]}>{statusNames[issue.status]}</Status>
                    </div>
                    <div className="m-queue-item-name">
                      {issue.lines
                        .map((line) => itemById(workspace.items, line.itemId).name)
                        .join(", ")}
                    </div>
                    <div className="m-queue-item-meta">
                      <span>
                        {kindNames[issue.kind]} · {issue.lines.length} dòng
                      </span>
                      {problem && <span className="m-shortage-label">Cần kiểm tra</span>}
                    </div>
                    <div className="m-queue-item-bottom">
                      <span>{creatorName(issue)}</span>
                      <span>
                        {new Date(issue.createdAt).toLocaleDateString("vi-VN", {
                          day: "2-digit",
                          month: "2-digit",
                        })}
                      </span>
                    </div>
                  </button>
                );
              })
            ) : (
              <div className="m-empty">
                <Search size={23} />
                <strong>Không có phiếu phù hợp</strong>
                <p>Thử đổi bộ lọc hoặc từ khóa tìm kiếm.</p>
                <ActionButton
                  onClick={() => {
                    setSearch("");
                    setFilter("all");
                    setKind("all");
                  }}
                >
                  Xóa bộ lọc
                </ActionButton>
              </div>
            )}
          </div>
          <footer className="m-queue-footer">{filtered.length} phiếu được hiển thị</footer>
        </section>
        <div className="m-approval-detail">
          <ActionButton
            className="m-back-to-list"
            variant="plain"
            onClick={() => setMobileDetail(false)}
          >
            <ArrowLeft size={16} />
            Danh sách phiếu
          </ActionButton>
          {selected ? (
            <Panel
              title="Chi tiết phiếu xuất"
              subtitle="Đối chiếu số lượng trước khi phê duyệt."
              action={
                <Status tone={statusTones[selected.status]}>{statusNames[selected.status]}</Status>
              }
            >
              <div className="m-panel-body">
                <div className="m-issue-title">
                  <div>
                    <h3 tabIndex={-1} ref={heading}>
                      {selected.code}
                    </h3>
                    <span>{kindNames[selected.kind]}</span>
                  </div>
                  <ClipboardCheck size={29} strokeWidth={1.3} />
                </div>
                <dl className="m-detail-grid">
                  <div>
                    <dt>Quản lý lập phiếu</dt>
                    <dd>{creatorName(selected)}</dd>
                  </div>
                  <div>
                    <dt>Ngày lập phiếu</dt>
                    <dd>{new Date(selected.createdAt).toLocaleDateString("vi-VN")}</dd>
                  </div>
                  <div className="m-detail-wide">
                    <dt>Chứng từ nguồn</dt>
                    <dd>{sourceName(selected)}</dd>
                  </div>
                </dl>
              </div>
              <div className="m-detail-table-title">
                Hàng hóa đề nghị xuất <span>{selected.lines.length} dòng</span>
              </div>
              <div className="m-table-scroll">
                <table className="m-table m-issue-table">
                  <thead>
                    <tr>
                      <th>Hàng hóa</th>
                      <th className="m-number">Đề nghị</th>
                      <th className="m-number">
                        {selected.status === "da_duyet" ? "Tồn trước" : "Tồn hiện tại"}
                      </th>
                      <th className="m-number">
                        {selected.status === "da_duyet" ? "Tồn sau" : "Tồn dự kiến"}
                      </th>
                      <th className="m-number">Đơn giá chốt</th>
                      <th className="m-number">Thành tiền</th>
                      <th>Kiểm tra</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selected.lines.map((line) => {
                      const item = itemById(workspace.items, line.itemId);
                      const posting = selected.posting?.find((entry) => entry.itemId === item.id);
                      const before = posting?.before ?? item.stock;
                      const after = posting?.after ?? item.stock - line.quantity;
                      return (
                        <tr key={line.itemId}>
                          <td>
                            <strong>{item.name}</strong>
                            <small>
                              {item.code} · SKU {item.sku} · {item.unit}
                            </small>
                          </td>
                          <td className="m-number">
                            <strong>{number(line.quantity)}</strong>
                          </td>
                          <td className="m-number">{number(before)}</td>
                          <td className={`m-number ${after < 0 ? "m-negative" : ""}`}>
                            {selected.status === "tu_choi" ? "—" : number(after)}
                          </td>
                          <td className="m-number">
                            {line.price === null ? "Chưa chốt" : money(line.price)}
                          </td>
                          <td className="m-number">
                            {line.price === null ? "—" : money(line.price * line.quantity)}
                          </td>
                          <td>
                            {selected.status === "da_duyet" ? (
                              <Check size={17} className="m-positive" aria-label="Đã xuất" />
                            ) : selected.status === "tu_choi" ? (
                              <span className="m-muted">Không xuất</span>
                            ) : (
                              <Status tone={after < 0 ? "red" : "green"}>
                                {after < 0 ? `Thiếu ${number(-after)}` : "Đủ tồn"}
                              </Status>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="m-panel-total">
                <span>Giá trị phiếu xuất</span>
                <strong>{selectedTotal === null ? "Chưa chốt giá" : money(selectedTotal)}</strong>
              </div>
              <div className="m-panel-body m-detail-notes">
                <Notice
                  tone={
                    selected.status === "da_duyet"
                      ? "green"
                      : selected.status === "tu_choi"
                        ? "neutral"
                        : selectedProblem
                          ? "amber"
                          : "green"
                  }
                >
                  {selected.status === "da_duyet"
                    ? "Đã ghi nhận xuất kho. Phiếu được khóa để tránh trừ tồn lần thứ hai."
                    : selected.status === "tu_choi"
                      ? "Phiếu đã bị từ chối, không làm thay đổi tồn kho."
                      : selectedProblem
                        ? selectedProblem
                        : "Phiếu đủ điều kiện theo dữ liệu demo hiện tại. Duyệt sẽ kiểm tra lại tồn và chốt giá từ mặt hàng."}
                </Notice>
                <p className="m-help">
                  Đơn giá và tổng tiền để trống trước duyệt. Khi duyệt, giá được lấy từ danh mục mặt
                  hàng và giữ nguyên trên phiếu.
                </p>
                {selected.status === "tu_choi" && (
                  <div className="m-note-block m-rejection-note">
                    <span>Lý do từ chối</span>
                    <p>{selected.reason}</p>
                  </div>
                )}
                <FormError error={approve.error ?? reject.error} />
              </div>
              <footer className="m-action-bar m-approval-actions">
                <span>
                  <ShieldCheck size={16} />
                  {selected.status === "cho_duyet"
                    ? "Chỉ ghi sổ sau khi duyệt"
                    : "Phiếu đã được xử lý"}
                </span>
                {selected.status === "cho_duyet" ? (
                  <div>
                    <ActionButton
                      variant="danger"
                      disabled={busy}
                      onClick={() => {
                        setReason("");
                        setDialog("reject");
                      }}
                    >
                      Từ chối
                    </ActionButton>
                    <ActionButton
                      variant="primary"
                      disabled={!!selectedProblem || busy}
                      onClick={() => setDialog("approve")}
                    >
                      <CheckCircle2 size={16} />
                      Duyệt xuất kho
                    </ActionButton>
                  </div>
                ) : (
                  <Status tone={statusTones[selected.status]}>
                    {statusNames[selected.status]}
                  </Status>
                )}
              </footer>
            </Panel>
          ) : (
            <div className="m-panel m-empty m-detail-empty">
              <ClipboardCheck size={32} />
              <h2>Chưa có phiếu để xem</h2>
              <p>Chọn một phiếu trong hàng chờ để đối chiếu chi tiết.</p>
            </div>
          )}
        </div>
      </div>
      {dialog && selected && (
        <ConfirmDialog
          title={dialog === "approve" ? `Duyệt ${selected.code}?` : `Từ chối ${selected.code}?`}
          confirmLabel={dialog === "approve" ? "Xác nhận duyệt xuất" : "Xác nhận từ chối"}
          danger={dialog === "reject"}
          busy={busy}
          onClose={() => setDialog(null)}
          onConfirm={() => {
            if (dialog === "reject" && !reason.trim()) {
              document.getElementById("reject-reason")?.focus();
              return;
            }
            void submit();
          }}
        >
          <p>
            {dialog === "approve"
              ? "Các vật tư sau sẽ được trừ khỏi tồn kho demo:"
              : "Lý do được lưu để quản lý đối chiếu phiếu bị từ chối."}
          </p>
          {dialog === "approve" ? (
            <ul className="m-confirm-lines">
              {selected.lines.map((line) => (
                <li key={line.itemId}>
                  <span>{itemById(workspace.items, line.itemId).name}</span>
                  <strong>
                    −{number(line.quantity)} {itemById(workspace.items, line.itemId).unit}
                  </strong>
                </li>
              ))}
            </ul>
          ) : (
            <Field label="Lý do từ chối" required>
              <textarea
                id="reject-reason"
                autoFocus
                rows={3}
                required
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Ví dụ: Số lượng đề nghị vượt nhu cầu của lệnh…"
              />
              <span className="m-help">Vui lòng nhập lý do trước khi xác nhận.</span>
            </Field>
          )}
          <FormError error={approve.error ?? reject.error} />
          {dialog === "approve" && (
            <Notice>
              Toàn bộ phiếu được xử lý cùng lúc. Không xuất một phần và không trừ tồn khi duyệt lại.
            </Notice>
          )}
        </ConfirmDialog>
      )}
      <div className="m-mobile-flow-hint">
        <ArrowRight size={15} />
        Dữ liệu thay đổi dùng chung với các màn nhập kho và tính nhu cầu.
      </div>
    </>
  );
}
