import { useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthProvider.jsx";
import { documentPermissions } from "../features/auth/permissions.js";
import { useWrite } from "../lib/api/useResources.js";
import { useFeedback } from "./FeedbackProvider.jsx";
import { Button } from "./Button.jsx";
import { SavedLines } from "./ResourceFields.jsx";
import { InfoGrid } from "./RecordPanel.jsx";
import { itemName } from "../lib/format.js";
export function ApprovalActions({
  kind,
  path,
  base,
  snapshot,
  items,
  dirty = false,
  allowedActions,
  assignedId,
}) {
  const record = snapshot.data;
  const { user } = useAuth();
  const permissions =
    allowedActions ?? documentPermissions(kind, user.ma_vai_tro, record, user.id, assignedId);
  const { confirm, notify } = useFeedback();
  const mutation = useWrite();
  const navigate = useNavigate();
  const reason = dirty ? "Lưu hoặc tải lại bản nháp trước khi thực hiện thao tác." : undefined;
  const employeeIssue = kind === "issue" && user.ma_vai_tro === "nhan_vien";
  const sendLabel = employeeIssue
    ? (record.trang_thai === "tu_choi" ? "Gửi lại" : "Gửi")
    : "Gửi duyệt";
  const sendTitle = employeeIssue ? `${sendLabel} phiếu xuất` : "Gửi duyệt chứng từ";
  const code = record.ma_phieu_xuat || record.ma_phieu;
  const content =
    kind === "issue" ? (
      <>
        {employeeIssue && (
          <InfoGrid entries={[["Yêu cầu sản xuất", `YCSX #${record.yeu_cau_san_xuat_id}`]]} />
        )}
        <SavedLines lines={record.chi_tiet} items={items} units={employeeIssue} />
      </>
    ) : (
      <InfoGrid
        entries={[
          ["Mặt hàng", itemName(items, record.mat_hang_id)],
          ["Số lượng hoàn thành", record.so_luong_hoan_thanh],
        ]}
      />
    );
  function act(action, title, options = {}) {
    confirm({
      title,
      description: `${code}. Kiểm tra nội dung chứng từ trước khi xác nhận.`,
      content,
      reason: options.reason,
      danger: options.danger,
      impact:
        action === "duyet"
          ? kind === "issue"
            ? "Duyệt thành công sẽ trừ tồn kho một lần và ghi giao dịch xuất. Chứng từ đã duyệt bất biến."
            : "Duyệt thành công sẽ cộng đầu ra sản xuất một lần; không trừ vật tư lần nữa."
          : employeeIssue
            ? "Chưa trừ tồn; hàng vẫn được giữ cho yêu cầu."
            : "Thao tác này chưa làm thay đổi tồn kho.",
      onConfirm: async (explanation) => {
        const result = await mutation.mutateAsync({
          path: `${path}/${record.id}${action ? `/${action}` : ""}`,
          method: action ? "post" : "delete",
          body: options.reason ? { ly_do: explanation } : {},
          etag: snapshot.etag,
        });
        notify(
          result.data?.da_ghi_so_truoc_do
            ? "Chứng từ đã ghi sổ trước đó; không ghi trùng."
            : `Đã xử lý ${code}.${result.data?.giao_dich_kho_ids?.length ? ` Giao dịch kho: ${result.data.giao_dich_kho_ids.join(", ")}.` : ""}`,
        );
        if (!action) navigate(base);
      },
    });
  }
  return (
    <div className="actions actions-end">
      {permissions.edit && (
        <Button
          variant="secondary"
          reason={reason}
          onClick={() => act("", "Xóa bản nháp", { danger: true })}
        >
          Xóa nháp
        </Button>
      )}
      {permissions.returnDraft && (
        <Button
          variant="secondary"
          onClick={() => act("ve_nhap", "Chuyển về bản nháp", { reason: true })}
        >
          Chuyển về bản nháp
        </Button>
      )}
      {permissions.send && (
        <Button reason={reason} onClick={() => act("gui", sendTitle)}>
          {sendLabel}
        </Button>
      )}
      {permissions.reject && (
        <Button
          variant="secondary"
          onClick={() => act("tu_choi", "Từ chối chứng từ", { reason: true, danger: true })}
        >
          Từ chối…
        </Button>
      )}
      {permissions.approve && (
        <Button
          onClick={() =>
            act("duyet", kind === "issue" ? "Duyệt phiếu xuất" : "Duyệt chứng từ hoàn thành")
          }
        >
          Duyệt {kind === "issue" ? "phiếu xuất" : "chứng từ"}
        </Button>
      )}
    </div>
  );
}
