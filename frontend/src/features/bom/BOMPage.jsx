import { useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useCollection, useDetail, useWrite } from "../../lib/api/useResources.js";
import { itemName, dateTime } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import {
  DocumentLines,
  newLine,
  linePayload,
  SavedLines,
} from "../../components/ResourceFields.jsx";
import { QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";

const base = "/kho/bom";
const newProduct = "/kho/mat-hang/moi?loai_mat_hang=thanh_pham";

// UC-15/16 — BOM v4 is one level; its initial version belongs to item creation.
export function BOMPage() {
  const { id } = useParams();
  const catalog = useCatalog();
  const collection = useCollection(API.bom, { sort: "-id" });
  const detail = useDetail(API.bom, id);
  const items = catalog.data?.data || [];
  if (id === "moi") return <Navigate to={newProduct} replace />;
  return (
    <>
      <PageHeader
        title="Công thức sản phẩm (BOM)"
        subtitle="BOM một cấp, nhiều phiên bản; mỗi thành phẩm có tối đa một phiên bản đang dùng."
        action={
          <Link className="btn btn-primary" to={newProduct}>
            Tạo thành phẩm
          </Link>
        }
      />
      <Collection
        collection={collection}
        search={false}
        pageSizes={[20, 50, 100]}
        filters={[
          {
            name: "mat_hang_id",
            label: "Mặt hàng",
            as: "select",
            options: [
              { value: "", label: "Tất cả" },
              ...items
                .filter((item) => item.loai_mat_hang === "thanh_pham")
                .map((item) => ({
                  value: item.id,
                  label: `${item.ma_mat_hang} · ${item.ten_mat_hang}`,
                })),
            ],
          },
          {
            name: "is_active",
            label: "Hiệu lực",
            as: "select",
            options: [
              { value: "", label: "Tất cả" },
              { value: "true", label: "Đang dùng" },
              { value: "false", label: "Ngừng dùng" },
            ],
          },
        ]}
        columns={[
          {
            key: "mat_hang_id",
            label: "Sản phẩm",
            render: (row) => (
              <Link to={`${base}/${row.id}`}>{itemName(items, row.mat_hang_id)}</Link>
            ),
          },
          { key: "version", label: "Phiên bản" },
          { key: "chi_tiet", label: "Thành phần", render: (row) => row.chi_tiet.length },
          {
            key: "is_active",
            label: "Hiệu lực",
            render: (row) => (
              <Badge status={row.is_active ? "hoat_dong" : "bi_khoa"}>
                {row.is_active ? "Đang dùng" : "Ngừng dùng"}
              </Badge>
            ),
          },
          {
            key: "action",
            label: "Thao tác",
            render: (row) => <Link to={`${base}/${row.id}`}>Mở →</Link>,
          },
        ]}
      />
      <RecordPanel id={id} query={detail} base={base} title="Chi tiết công thức BOM">
        {(snapshot) => (
          <QueryState query={catalog}>
            {snapshot && <BomDetail snapshot={snapshot} items={items} />}
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}

// UC-17 — the version request carries only the formula and the ETag reviewed by QLK.
function BomVersionForm({ snapshot, items, onCancel }) {
  const record = snapshot.data;
  const [lines, setLines] = useState(() =>
    record.chi_tiet.map((line) =>
      newLine({ mat_hang_id: String(line.mat_hang_id), so_luong: String(line.so_luong) }),
    ),
  );
  const mutation = useWrite();
  const { confirm, notify } = useFeedback();
  const navigate = useNavigate();
  function submit(event) {
    event.preventDefault();
    const body = { chi_tiet: linePayload(lines) };
    confirm({
      title: "Tạo và kích hoạt phiên bản BOM",
      description: `${itemName(items, record.mat_hang_id)} · phiên bản nguồn ${record.version}.`,
      content: <SavedLines lines={body.chi_tiet} items={items} />,
      impact:
        "Kích hoạt phiên bản mới và ngừng phiên bản hiện hành. Yêu cầu đã gửi giữ nguyên BOM đã chốt; không đổi tồn kho.",
      onConfirm: async () => {
        const result = await mutation.mutateAsync({
          path: `${API.bom}/${record.id}/phien_ban`,
          body,
          etag: snapshot.etag,
        });
        notify("Đã tạo và kích hoạt phiên bản BOM.");
        onCancel();
        navigate(`${base}/${result.data.id}`);
      },
    });
  }
  return (
    <form className="stack" onSubmit={submit}>
      <h3>Định mức phiên bản mới</h3>
      <DocumentLines
        lines={lines}
        onChange={setLines}
        items={items}
        outputId={record.mat_hang_id}
        types={["linh_kien"]}
      />
      <div className="actions actions-end">
        <Button variant="secondary" onClick={onCancel}>
          Hủy chỉnh sửa
        </Button>
        <Button type="submit" disabled={mutation.isPending}>
          Tạo và kích hoạt phiên bản
        </Button>
      </div>
    </form>
  );
}

// UC-18/19 — changing lifecycle uses the selected version's validator, never deletes its data.
function BomDetail({ snapshot, items }) {
  const record = snapshot.data;
  const [drafting, setDrafting] = useState(false);
  const { confirm, notify } = useFeedback();
  const write = useWrite();
  function changeActive() {
    confirm({
      title: record.is_active ? "Ngừng dùng BOM" : "Dùng lại phiên bản BOM",
      description: `${itemName(items, record.mat_hang_id)} · phiên bản ${record.version}.`,
      impact: record.is_active
        ? "Ngừng công thức và thành phẩm. Giữ nguyên số dư và chứng từ cũ."
        : "Dùng lại phiên bản được chọn cùng thành phẩm, thay phiên bản hiện hành. Không đổi tồn kho.",
      danger: record.is_active,
      onConfirm: async () => {
        await write.mutateAsync({
          path: `${API.bom}/${record.id}${record.is_active ? "" : "/kich_hoat"}`,
          method: record.is_active ? "delete" : "post",
          body: record.is_active ? null : {},
          etag: snapshot.etag,
        });
        notify("Đã cập nhật hiệu lực BOM.");
      },
    });
  }
  return (
    <div className="stack">
      <InfoGrid
        entries={[
          ["Sản phẩm", itemName(items, record.mat_hang_id)],
          ["Phiên bản", record.version],
          ["Tạo lúc", dateTime(record.created_at)],
          ["Kích hoạt gần nhất", dateTime(record.kich_hoat_gan_nhat_at)],
          [
            "Hiệu lực",
            <Badge key="state" status={record.is_active ? "hoat_dong" : "bi_khoa"}>
              {record.is_active ? "Đang dùng" : "Ngừng dùng"}
            </Badge>,
          ],
        ]}
      />
      {drafting ? (
        <BomVersionForm snapshot={snapshot} items={items} onCancel={() => setDrafting(false)} />
      ) : (
        <>
          <SavedLines lines={record.chi_tiet} items={items} />
          <div className="actions">
            <Button
              variant={record.is_active ? "danger" : "secondary"}
              onClick={changeActive}
              disabled={write.isPending}
            >
              {record.is_active ? "Ngừng dùng phiên bản" : "Dùng lại phiên bản"}
            </Button>
            <Button onClick={() => setDrafting(true)}>Tạo phiên bản mới</Button>
          </div>
        </>
      )}
    </div>
  );
}
