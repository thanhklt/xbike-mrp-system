import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/Button";
import {
  adjustmentLines,
  changeOrder,
  confirmAdjustment,
  date,
  effective,
  fmt,
  label,
  orderBlock,
  referenced,
  saveItem,
  stock,
  type Adjustment,
  type Item,
  type ItemType,
  type OrderAction,
  type Page,
} from "./model";
import { Details, Field, Modal, Notice, Status, Table, useDemo } from "./shared";

interface Props {
  page: Page;
  id: string;
  onClose: () => void;
  conflict: boolean;
  source?: string;
}
export function Detail(props: Props) {
  const { db, role } = useDemo();
  if (role === "A" || (role === "N" && !["mathang", "lenhsanxuat"].includes(props.page)))
    return null;
  const found =
    props.id === "new"
      ? role === "Q" && ["mathang", "dieuchinhkho"].includes(props.page)
      : props.page === "mathang"
        ? db.items.some((x) => x.id === Number(props.id))
        : props.page === "giaodichkho"
          ? db.ledger.some((x) => x.id === Number(props.id))
          : props.page === "dieuchinhkho"
            ? db.adjustments.some((x) => x.id === Number(props.id))
            : db.orders.some(
                (x) => x.id === Number(props.id) && (role !== "N" || x.nhan_vien_id === 21),
              );
  if (!found)
    return (
      <Modal title="Không mở được chi tiết" onClose={props.onClose}>
        <Notice>
          Tài nguyên không tồn tại hoặc nằm ngoài phạm vi được xem. Hãy quay lại danh sách.
        </Notice>
      </Modal>
    );
  return props.page === "mathang" ? (
    <ItemDetail {...props} />
  ) : props.page === "lenhsanxuat" ? (
    <OrderDetail {...props} />
  ) : props.page === "giaodichkho" ? (
    <LedgerDetail {...props} />
  ) : (
    <AdjustmentDetail {...props} />
  );
}
function ItemDetail({ id, onClose, conflict }: Props) {
  const { db, role, mutate } = useDemo();
  const item = db.items.find((x) => x.id === Number(id));
  const [mode, setMode] = useState<"view" | "edit" | "disable">(item ? "view" : "edit");
  const locked = !!item && referenced(db, item.id);
  if (mode === "edit")
    return (
      <Modal
        title={item ? "Chỉnh sửa mặt hàng" : "Thêm mặt hàng"}
        onClose={onClose}
        conflict={conflict}
        submitLabel="Lưu mặt hàng"
        onSubmit={(data) => {
          const value = (key: string) => String(data.get(key) || "").trim();
          const candidate: Item = {
            id: item?.id ?? Math.max(0, ...db.items.map((x) => x.id)) + 1,
            ma_mat_hang: value("ma_mat_hang"),
            sku: value("sku"),
            ten_mat_hang: value("ten_mat_hang"),
            loai_mat_hang: (locked ? item!.loai_mat_hang : value("loai_mat_hang")) as ItemType,
            don_vi_tinh: value("don_vi_tinh"),
            don_gia: Number(value("don_gia")),
            mau_sac: value("mau_sac"),
            mo_ta: value("mo_ta"),
            is_active: item?.is_active ?? true,
          };
          mutate((next) => saveItem(next, role, candidate));
          onClose();
        }}
      >
        {locked && (
          <Notice>
            Mã, SKU, loại và đơn vị đã có tham chiếu nên được khóa. Bạn vẫn có thể cập nhật tên, giá
            và mô tả.
          </Notice>
        )}
        <div className="op-form-grid">
          <Field label="Mã mặt hàng *" hint="MH-NNNNNN, khác MH-000000">
            <input
              name="ma_mat_hang"
              required
              pattern="MH-(?!000000)[0-9]{6}"
              defaultValue={item?.ma_mat_hang}
              readOnly={locked}
            />
          </Field>
          <Field label="SKU *">
            <input name="sku" required defaultValue={item?.sku} readOnly={locked} />
          </Field>
          <Field label="Tên mặt hàng *">
            <input name="ten_mat_hang" required defaultValue={item?.ten_mat_hang} />
          </Field>
          <Field label="Loại mặt hàng *">
            <select
              name="loai_mat_hang"
              defaultValue={item?.loai_mat_hang || "nguyen_vat_lieu"}
              disabled={locked}
            >
              {["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"].map((v) => (
                <option key={v} value={v}>
                  {label(v)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Đơn vị tính *" hint="Không dấu, ví dụ: cay, cai, bo">
            <input
              name="don_vi_tinh"
              required
              pattern="[a-z][a-z0-9]*(_[a-z0-9]+)*"
              defaultValue={item?.don_vi_tinh || "cai"}
              readOnly={locked}
            />
          </Field>
          <Field label="Đơn giá (₫) *">
            <input
              name="don_gia"
              type="number"
              min="0"
              step="1"
              max={Number.MAX_SAFE_INTEGER}
              required
              defaultValue={item?.don_gia}
            />
          </Field>
          <Field label="Màu sắc" hint="Không dấu, ví dụ: xanh_navy">
            <input
              name="mau_sac"
              pattern="[a-z][a-z0-9]*(_[a-z0-9]+)*"
              defaultValue={item?.mau_sac}
            />
          </Field>
          <Field label="Mô tả">
            <textarea name="mo_ta" defaultValue={item?.mo_ta} />
          </Field>
        </div>
        <Notice>
          Tồn kho chỉ thay đổi qua chứng từ đã ghi sổ. Đơn giá mới không thay đổi các phiếu xuất đã
          chốt.
        </Notice>
      </Modal>
    );
  if (!item) return null;
  if (mode === "disable")
    return (
      <Modal
        title={item.is_active ? "Ngừng hoạt động mặt hàng" : "Kích hoạt lại mặt hàng"}
        onClose={onClose}
        conflict={conflict}
        submitLabel="Xác nhận"
        onSubmit={() => {
          mutate((next) => {
            if (role !== "Q") throw new Error("Chỉ quản lý được thay đổi danh mục.");
            next.items.find((x) => x.id === item.id)!.is_active = !item.is_active;
          });
          onClose();
        }}
      >
        <p>
          <strong>{item.ten_mat_hang}</strong>
        </p>
        <Notice>
          {item.is_active
            ? "Mặt hàng vẫn được lưu trong lịch sử nhưng không thể dùng cho chứng từ mới."
            : "Mặt hàng sẽ được dùng trở lại trong chứng từ mới."}{" "}
          Tồn kho {fmt(stock(db, item.id))} {label(item.don_vi_tinh)} giữ nguyên.
        </Notice>
      </Modal>
    );
  return (
    <Modal title={item.ten_mat_hang} onClose={onClose}>
      <Status value={item.is_active ? "active" : "inactive"} />
      <Details
        values={[
          ["Mã mặt hàng", item.ma_mat_hang],
          ["SKU", item.sku],
          ["Loại", label(item.loai_mat_hang)],
          ["Đơn vị", label(item.don_vi_tinh)],
          ["Đơn giá", `${fmt(item.don_gia)} ₫`],
          ["Tồn hiện tại", `${fmt(stock(db, item.id))} ${label(item.don_vi_tinh)}`],
          ["Màu sắc", label(item.mau_sac) || "—"],
          ["Mô tả", item.mo_ta || "—"],
        ]}
      />
      <Notice>Tồn kho tính từ giao dịch đã ghi sổ, không sửa trực tiếp.</Notice>
      {role === "Q" && (
        <div className="op-actions">
          <Button onClick={() => setMode("edit")}>Chỉnh sửa</Button>
          <Button variant="secondary" onClick={() => setMode("disable")}>
            {item.is_active ? "Ngừng hoạt động" : "Kích hoạt lại"}
          </Button>
        </div>
      )}
    </Modal>
  );
}
function OrderDetail({ id, onClose, conflict }: Props) {
  const { db, role, mutate } = useDemo();
  const order = db.orders.find((x) => x.id === Number(id))!;
  const [action, setAction] = useState<OrderAction | null>(null);
  const names: Record<OrderAction, string> = {
    assign: "Giao người thực hiện",
    send: "Gửi lệnh sản xuất",
    start: "Bắt đầu thực hiện",
    cancel: "Hủy lệnh sản xuất",
  };
  if (action)
    return (
      <Modal
        title={names[action]}
        onClose={onClose}
        conflict={conflict}
        submitLabel={names[action]}
        onSubmit={(data) => {
          mutate((next) =>
            changeOrder(next, role, order.id, action, String(data.get("value") || "")),
          );
          setAction(null);
        }}
      >
        <p>{order.ma_lenh_san_xuat}</p>
        {action === "assign" ? (
          <Field label="Người thực hiện">
            <select name="value" defaultValue={order.nhan_vien_id || ""}>
              <option value="">Chưa giao</option>
              {Object.entries(db.names)
                .filter(([key]) => key !== "10")
                .map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
            </select>
          </Field>
        ) : action === "cancel" ? (
          <Field label="Lý do hủy *">
            <textarea name="value" required />
          </Field>
        ) : (
          <Notice>
            {action === "send"
              ? "Gửi lệnh đến người được giao. Thiếu vật tư không chặn gửi lệnh; chỉ bắt đầu sau khi đã được cấp đủ."
              : "Bắt đầu công việc được giao. Thao tác này không thay đổi tồn kho."}
          </Notice>
        )}
      </Modal>
    );
  const item = db.items.find((x) => x.id === order.mat_hang_id)!;
  const children = db.orders.filter((x) => x.lenh_san_xuat_cha_id === order.id);
  const actions: OrderAction[] = role === "Q" ? ["assign", "send", "cancel"] : ["start"];
  return (
    <Modal title={order.ma_lenh_san_xuat} onClose={onClose}>
      <Status value={order.trang_thai} />
      <h3>{item.ten_mat_hang}</h3>
      <Details
        values={[
          ["Người thực hiện", db.names[order.nhan_vien_id || ""] || "Chưa giao"],
          ["Yêu cầu sản xuất", `YCSX-202611-${String(order.yeu_cau_san_xuat_id).padStart(6, "0")}`],
          [
            "Đầu ra đã duyệt",
            `${fmt(order.so_luong_da_hoan_thanh)} / ${fmt(order.so_luong)} ${label(item.don_vi_tinh)}`,
          ],
          ["Còn phải hoàn thành", fmt(order.so_luong - order.so_luong_da_hoan_thanh)],
          ["Định mức", `BOM #${order.bom_id}`],
          ["Ngày tạo", date(order.created_at)],
          ["Bắt đầu", date(order.started_at)],
          ["Hoàn thành", date(order.completed_at)],
        ]}
      />
      <h3>Tình trạng cấp vật tư</h3>
      <Table headers={["Vật tư", "Cần", "Đã cấp", "Còn cấp", "Tồn kho"]}>
        {order.vat_tu.map((line) => (
          <tr key={line.mat_hang_id}>
            <td>
              {db.items.find((x) => x.id === line.mat_hang_id)?.ten_mat_hang}
              <small>{label(db.items.find((x) => x.id === line.mat_hang_id)!.don_vi_tinh)}</small>
            </td>
            <td className="op-num">{fmt(line.so_luong_can)}</td>
            <td className="op-num">{fmt(line.so_luong_da_cap)}</td>
            <td className="op-num">{fmt(line.so_luong_can - line.so_luong_da_cap)}</td>
            <td className="op-num">{fmt(stock(db, line.mat_hang_id))}</td>
          </tr>
        ))}
      </Table>
      <Notice
        tone={order.vat_tu.some((x) => x.so_luong_da_cap < x.so_luong_can) ? "warning" : "good"}
      >
        {order.vat_tu.some((x) => x.so_luong_da_cap < x.so_luong_can)
          ? "Chưa cấp đủ vật tư; chưa thể bắt đầu."
          : "Đã cấp đủ vật tư cho lệnh."}{" "}
        Số đã cấp chỉ tính phiếu xuất đã duyệt.
      </Notice>
      {order.lenh_san_xuat_cha_id && (
        <p>
          Lệnh cha:{" "}
          <Link to={`?id=${order.lenh_san_xuat_cha_id}`}>
            {db.orders.find((x) => x.id === order.lenh_san_xuat_cha_id)?.ma_lenh_san_xuat}
          </Link>
        </p>
      )}
      {children.length > 0 && (
        <>
          <h3>Lệnh con</h3>
          {children.map((child) => (
            <p className="op-source" key={child.id}>
              <Link to={`?id=${child.id}`}>{child.ma_lenh_san_xuat}</Link>
              <Status value={child.trang_thai} />
            </p>
          ))}
        </>
      )}
      {order.ly_do_huy && <Notice>Lý do hủy: {order.ly_do_huy}</Notice>}
      <p className="op-muted">
        Lệnh tự hoàn thành khi đầu ra được duyệt đủ số lượng; không có thao tác hoàn tất trực tiếp.
      </p>
      <div className="op-action-list">
        {actions.map((value) => {
          const reason = orderBlock(db, role, order, value);
          return (
            <div key={value}>
              <Button
                variant={value === "cancel" ? "secondary" : "primary"}
                disabled={!!reason}
                aria-describedby={`reason-${value}`}
                onClick={() => setAction(value)}
              >
                {names[value]}
              </Button>
              {reason && <small id={`reason-${value}`}>{reason}</small>}
            </div>
          );
        })}
      </div>
    </Modal>
  );
}
function LedgerDetail({ id, onClose }: Props) {
  const { db } = useDemo();
  const entry = db.ledger.find((x) => x.id === Number(id))!;
  const item = db.items.find((x) => x.id === entry.mat_hang_id)!;
  const incoming = entry.loai_giao_dich === "nhap_vat_tu";
  const related = db.adjustments.filter(
    (x) =>
      x.trang_thai === "da_xac_nhan" &&
      x.chi_tiet.some((line) => line.giao_dich_goc_id === entry.id),
  );
  return (
    <Modal title={`Giao dịch GD-${entry.id}`} onClose={onClose}>
      <Status value={entry.loai_giao_dich} />
      <Details
        values={[
          ["Mặt hàng", item.ten_mat_hang],
          [
            "Biến động",
            <span className={entry.so_luong_bien_dong < 0 ? "op-negative" : "op-positive"}>
              {entry.so_luong_bien_dong > 0 ? "+" : ""}
              {fmt(entry.so_luong_bien_dong)} {label(item.don_vi_tinh)}
            </span>,
          ],
          ["Chứng từ nguồn", entry.source],
          ["Người thực hiện", db.names[entry.nhan_vien_id]],
          ["Thời điểm ghi sổ", date(entry.posted_at)],
        ]}
      />
      {incoming ? (
        <>
          <h3>Đối chiếu lượng nhập</h3>
          <Notice>
            Lượng nhập gốc <strong>{fmt(entry.so_luong_bien_dong)}</strong> → Hiệu lực{" "}
            <strong>
              {fmt(effective(db, entry.id))} {label(item.don_vi_tinh)}
            </strong>
            . Đã tính {related.length} phiếu điều chỉnh được xác nhận.
          </Notice>
          {related.map((x) => (
            <p className="op-source" key={x.id}>
              <Link to={`/dieuchinhkho?id=${x.id}`}>{x.ma_phieu}</Link>
              <Status value={x.trang_thai} />
            </p>
          ))}
          <Link className="op-link-action" to={`/dieuchinhkho?id=new&source=${entry.id}`}>
            Lập phiếu điều chỉnh
          </Link>
        </>
      ) : (
        <Notice>
          Giao dịch đã ghi sổ chỉ đọc. Lượng hiệu lực chỉ áp dụng cho giao dịch nhập vật tư.
        </Notice>
      )}
      {entry.loai_giao_dich === "dieu_chinh_ton_kho" && (
        <Link to={`/dieuchinhkho?id=${entry.source_id}`}>Xem phiếu điều chỉnh nguồn</Link>
      )}
    </Modal>
  );
}
function AdjustmentTable({ entry, preview = false }: { entry: Adjustment; preview?: boolean }) {
  const { db } = useDemo();
  return (
    <Table
      headers={[
        "Mặt hàng / Nguồn",
        "Hiệu lực trước",
        "Số lượng đúng",
        "Chênh lệch",
        ...(preview ? ["Tồn sau"] : []),
      ]}
    >
      {entry.chi_tiet.map((line) => {
        const before = preview
          ? effective(db, line.giao_dich_goc_id)
          : line.so_luong_hieu_luc_truoc;
        const delta = preview ? line.so_luong_dung - before : line.so_luong_bien_dong;
        return (
          <tr key={line.giao_dich_goc_id}>
            <td>
              {db.items.find((x) => x.id === line.mat_hang_id)?.ten_mat_hang}
              <small>GD-{line.giao_dich_goc_id}</small>
            </td>
            <td className="op-num">{fmt(before)}</td>
            <td className="op-num">{fmt(line.so_luong_dung)}</td>
            <td className={`op-num ${delta < 0 ? "op-negative" : "op-positive"}`}>
              {delta > 0 ? "+" : ""}
              {fmt(delta)}
            </td>
            {preview && <td className="op-num">{fmt(stock(db, line.mat_hang_id) + delta)}</td>}
          </tr>
        );
      })}
    </Table>
  );
}
function AdjustmentDetail(props: Props) {
  const { db, role, mutate } = useDemo();
  const entry = db.adjustments.find((x) => x.id === Number(props.id));
  const [mode, setMode] = useState<"view" | "edit" | "confirm" | "delete">(entry ? "view" : "edit");
  if (mode === "edit") return <AdjustmentForm {...props} entry={entry} />;
  if (!entry) return null;
  if (mode === "confirm" || mode === "delete")
    return (
      <Modal
        title={mode === "confirm" ? "Xác nhận và ghi sổ" : "Xóa phiếu nháp"}
        onClose={props.onClose}
        conflict={props.conflict}
        submitLabel={mode === "confirm" ? "Xác nhận và ghi sổ" : "Xóa phiếu nháp"}
        onSubmit={() => {
          if (mode === "confirm") {
            mutate((next) => confirmAdjustment(next, role, entry.id));
            setMode("view");
          } else {
            mutate((next) => {
              const current = next.adjustments.find((x) => x.id === entry.id);
              if (role !== "Q" || current?.trang_thai !== "nhap")
                throw new Error("Chỉ quản lý được xóa phiếu nháp.");
              next.adjustments = next.adjustments.filter((x) => x.id !== entry.id);
            });
            props.onClose();
          }
        }}
      >
        <p>{entry.ma_phieu}</p>
        {mode === "confirm" ? (
          <>
            <AdjustmentTable entry={entry} preview />
            <Notice tone="warning">
              Kiểm tra số lượng và tồn sau điều chỉnh. Nếu có dòng làm tồn âm, toàn bộ phiếu sẽ
              không ghi sổ và tạo ticket demo. Phiếu đã xác nhận hoặc lỗi không thể sửa.
            </Notice>
          </>
        ) : (
          <Notice>Phiếu chưa ghi sổ. Xóa phiếu nháp không thay đổi tồn kho.</Notice>
        )}
      </Modal>
    );
  const ticket = db.tickets.find((x) => x.id === entry.ticket_id);
  return (
    <Modal title={entry.ma_phieu} onClose={props.onClose}>
      <Status value={entry.trang_thai} />
      <Details
        values={[
          ["Phiếu nhập nguồn", `PN-202611-${String(entry.phieu_nhap_id).padStart(6, "0")}`],
          ["Người lập", db.names[entry.nhan_vien_id]],
          ["Ngày lập", date(entry.created_at)],
          ["Ngày xác nhận", date(entry.confirmed_at)],
        ]}
      />
      <h3>Lý do điều chỉnh</h3>
      <p>{entry.ly_do}</p>
      <h3>Chi tiết điều chỉnh</h3>
      <AdjustmentTable entry={entry} />
      <Notice
        tone={entry.trang_thai === "loi" ? "bad" : entry.trang_thai === "da_xac_nhan" ? "good" : ""}
      >
        {entry.trang_thai === "nhap"
          ? "Phiếu nháp chưa thay đổi tồn kho. Chênh lệch được tính lại khi xác nhận."
          : entry.trang_thai === "loi"
            ? "Điều chỉnh thất bại; tồn kho giữ nguyên. Phiếu lỗi không thể sửa hoặc xác nhận lại. Hãy tạo phiếu mới để thử lại."
            : "Đã ghi sổ toàn bộ chênh lệch. Phiếu đã chốt và không thể chỉnh sửa."}
      </Notice>
      {ticket && (
        <Notice>
          <strong>{ticket.ma_ticket} · Chờ xử lý</strong>
          <p>{ticket.mo_ta_loi}</p>Đóng ticket không làm thay đổi tồn kho. Xử lý ticket ngoài phạm
          vi bản demo này.
        </Notice>
      )}
      {entry.trang_thai === "nhap" && (
        <div className="op-actions">
          <Button onClick={() => setMode("confirm")}>Xác nhận điều chỉnh</Button>
          <Button variant="secondary" onClick={() => setMode("edit")}>
            Chỉnh sửa
          </Button>
          <Button variant="secondary" onClick={() => setMode("delete")}>
            Xóa phiếu nháp
          </Button>
        </div>
      )}
      {entry.trang_thai === "loi" && <Link to="?id=new">Tạo phiếu mới</Link>}
    </Modal>
  );
}
function AdjustmentForm({ entry, source, onClose, conflict }: Props & { entry?: Adjustment }) {
  const { db, role, mutate } = useDemo();
  const receipt =
    entry?.phieu_nhap_id ||
    db.ledger.find((x) => x.id === Number(source) && x.loai_giao_dich === "nhap_vat_tu")
      ?.source_id ||
    41;
  const sources = db.ledger.filter(
    (x) => x.loai_giao_dich === "nhap_vat_tu" && x.source_id === receipt,
  );
  const [selected, setSelected] = useState<number[]>(
    entry?.chi_tiet.map((x) => x.giao_dich_goc_id) || (source ? [Number(source)] : []),
  );
  const [quantities, setQuantities] = useState<Record<number, string>>(() =>
    Object.fromEntries(
      sources.map((x) => [
        x.id,
        String(
          entry?.chi_tiet.find((v) => v.giao_dich_goc_id === x.id)?.so_luong_dung ??
            effective(db, x.id),
        ),
      ]),
    ),
  );
  return (
    <Modal
      title={entry ? "Chỉnh sửa phiếu điều chỉnh" : "Tạo phiếu điều chỉnh"}
      onClose={onClose}
      conflict={conflict}
      submitLabel="Lưu phiếu nháp"
      onSubmit={(data) => {
        mutate((next) => {
          if (role !== "Q") throw new Error("Chỉ quản lý được lập phiếu điều chỉnh.");
          const reason = String(data.get("reason") || "").trim();
          if (!reason) throw new Error("Lý do điều chỉnh không được để trống.");
          const lines = adjustmentLines(
            next,
            selected.map((id) => ({
              source: id,
              quantity: quantities[id] === "" ? NaN : Number(quantities[id]),
            })),
            receipt,
          );
          if (entry) {
            const current = next.adjustments.find((x) => x.id === entry.id);
            if (current?.trang_thai !== "nhap") throw new Error("Chỉ được sửa phiếu nháp.");
            Object.assign(current, { ly_do: reason, chi_tiet: lines });
          } else {
            const id = next.nextAdjustmentId++;
            next.adjustments.unshift({
              id,
              ma_phieu: `DCK-202611-${String(id - 300).padStart(6, "0")}`,
              phieu_nhap_id: receipt,
              nhan_vien_id: 10,
              trang_thai: "nhap",
              ly_do: reason,
              created_at: new Date().toISOString(),
              confirmed_at: null,
              chi_tiet: lines,
            });
          }
          return "Đã lưu phiếu nháp. Tồn kho chưa thay đổi.";
        });
        onClose();
      }}
    >
      <Field label="Phiếu nhập nguồn">
        <input readOnly value={`PN-202611-${String(receipt).padStart(6, "0")} · Đã hoàn thành`} />
      </Field>
      <Field label="Lý do điều chỉnh *">
        <textarea
          name="reason"
          required
          defaultValue={entry?.ly_do}
          placeholder="Ghi kết quả đối soát và lý do sửa số lượng…"
        />
      </Field>
      <h3>Chọn dòng cần điều chỉnh</h3>
      <p className="op-muted">
        Nhập số lượng đúng, không nhập lượng tăng/giảm. Có thể điều chỉnh về 0.
      </p>
      <Table
        headers={["Chọn / Mặt hàng", "Hiệu lực", "Số lượng đúng", "Chênh lệch", "Tồn trước → sau"]}
      >
        {sources.map((x) => {
          const item = db.items.find((i) => i.id === x.mat_hang_id)!;
          const checked = selected.includes(x.id);
          const valid =
            quantities[x.id] !== "" &&
            Number.isSafeInteger(Number(quantities[x.id])) &&
            Number(quantities[x.id]) >= 0;
          const delta = checked && valid ? Number(quantities[x.id]) - effective(db, x.id) : 0;
          return (
            <tr key={x.id}>
              <td>
                <label className="op-check">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) =>
                      setSelected((values) =>
                        event.target.checked ? [...values, x.id] : values.filter((v) => v !== x.id),
                      )
                    }
                  />
                  <span>
                    {item.ten_mat_hang}
                    <small>
                      GD-{x.id} · {label(item.don_vi_tinh)}
                    </small>
                  </span>
                </label>
              </td>
              <td className="op-num">{fmt(effective(db, x.id))}</td>
              <td>
                <input
                  aria-label={`Số lượng đúng ${item.ten_mat_hang}`}
                  type="number"
                  min="0"
                  step="1"
                  required={checked}
                  disabled={!checked}
                  value={quantities[x.id]}
                  onChange={(event) =>
                    setQuantities((values) => ({ ...values, [x.id]: event.target.value }))
                  }
                />
              </td>
              <td className={`op-num ${delta < 0 ? "op-negative" : ""}`}>
                {checked && !valid ? "—" : `${delta > 0 ? "+" : ""}${fmt(delta)}`}
              </td>
              <td className="op-num">
                {fmt(stock(db, item.id))} →{" "}
                <strong className={stock(db, item.id) + delta < 0 ? "op-negative" : ""}>
                  {checked && !valid ? "—" : fmt(stock(db, item.id) + delta)}
                </strong>
              </td>
            </tr>
          );
        })}
      </Table>
      <Notice tone="warning">
        Lưu nháp chưa thay đổi tồn kho. Chỉ xác nhận thành công mới ghi sổ toàn bộ phiếu.
      </Notice>
    </Modal>
  );
}
