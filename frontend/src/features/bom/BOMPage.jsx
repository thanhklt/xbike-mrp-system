import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import {
  useCatalog,
  useCollection,
  useDetail,
  useResource,
  useWrite,
} from "../../lib/api/useResources.js";
import { itemName, dateTime } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import {
  ItemSelect,
  DocumentLines,
  newLine,
  linePayload,
  SavedLines,
} from "../../components/ResourceFields.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
const base = "/kho/bom";
export function BOMPage() {
  const { id } = useParams();
  const catalog = useCatalog();
  const collection = useCollection(API.bom, { sort: "-id" });
  const detail = useDetail(API.bom, id);
  const items = catalog.data?.data || [];
  return (
    <>
      <PageHeader
        title="Công thức sản phẩm (BOM)"
        subtitle="BOM nhiều cấp, nhiều phiên bản; mỗi mặt hàng có tối đa một phiên bản hiện hành."
        action={
          <Link className="btn btn-primary" to={`${base}/moi`}>
            Tạo BOM mới
          </Link>
        }
      />
      <div>
        <Collection
          collection={collection}
          search={false}
          filters={[
            {
              name: "mat_hang_id",
              label: "Mặt hàng",
              as: "select",
              options: [
                { value: "", label: "Tất cả" },
                ...items
                  .filter((item) => ["thanh_pham", "ban_thanh_pham"].includes(item.loai_mat_hang))
                  .map((item) => ({ value: item.id, label: item.ten_mat_hang })),
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
                <Badge status={row.is_active ? "hoat_dong" : "nhap"}>
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
        <RecordPanel
          id={id}
          query={detail}
          base={base}
          title={id === "moi" ? "Tạo phiên bản BOM" : "Chi tiết và cấu trúc BOM"}
        >
          {(snapshot) =>
            snapshot ? (
              <BomDetail record={snapshot.data} items={items} />
            ) : (
              <QueryState query={catalog}>
                <BomForm items={items} />
              </QueryState>
            )
          }
        </RecordPanel>
      </div>
    </>
  );
}
function BomForm({ items }) {
  const [outputId, setOutputId] = useState("");
  const [lines, setLines] = useState([newLine()]);
  const mutation = useWrite();
  const { confirm, notify } = useFeedback();
  const navigate = useNavigate();
  function submit(event) {
    event.preventDefault();
    const body = { mat_hang_id: Number(outputId), chi_tiet: linePayload(lines) };
    confirm({
      title: "Tạo và kích hoạt phiên bản BOM",
      description: `${itemName(items, outputId)}. Kiểm tra định mức cho một đơn vị đầu ra.`,
      content: <SavedLines lines={body.chi_tiet} items={items} />,
      impact:
        "API tạo BOM đồng thời kích hoạt phiên bản mới và ngừng phiên bản hiện hành. Không đổi tồn kho; các kế hoạch đã chốt giữ BOM cũ.",
      onConfirm: async () => {
        const result = await mutation.mutateAsync({ path: API.bom, body, versioned: false });
        notify("Đã tạo và kích hoạt phiên bản BOM.");
        navigate(`${base}/${result.data.id}`);
      },
    });
  }
  return (
    <form className="stack" onSubmit={submit}>
      <ItemSelect
        label="Sản phẩm đầu ra"
        required
        value={outputId}
        onChange={(event) => {
          setOutputId(event.target.value);
          setLines([newLine()]);
        }}
        items={items}
        types={["thanh_pham", "ban_thanh_pham"]}
      />
      <DocumentLines
        lines={lines}
        onChange={setLines}
        items={items}
        outputId={outputId}
        types={["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham"]}
      />
      <Notice>
        Định mức cho một đơn vị đầu ra phải là số nguyên dương; không trùng mặt hàng hoặc tạo chu
        trình. Tạo mới sẽ kích hoạt phiên bản và ngừng phiên bản hiện hành. Nội dung đã lưu bất
        biến.
      </Notice>
      <Button type="submit" disabled={mutation.isPending}>
        Tạo và kích hoạt phiên bản
      </Button>
    </form>
  );
}
function BomDetail({ record, items }) {
  const tree = useResource(`${API.bom}/${record.id}/cau_truc`);
  const { confirm, notify } = useFeedback();
  const write = useWrite();
  function changeActive() {
    confirm({
      title: record.is_active ? "Ngừng dùng BOM" : "Kích hoạt phiên bản BOM",
      description: `${itemName(items, record.mat_hang_id)} · phiên bản ${record.version}. Kích hoạt sẽ ngừng dùng phiên bản hiện hành; kế hoạch đã chốt giữ BOM cũ.`,
      onConfirm: async () => {
        await write.mutateAsync({
          path: `${API.bom}/${record.id}${record.is_active ? "" : "/kich_hoat"}`,
          method: record.is_active ? "delete" : "post",
          versioned: false,
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
          ["Bắt đầu hiệu lực", dateTime(record.start_time)],
          ["Kết thúc hiệu lực", dateTime(record.end_time)],
        ]}
      />
      <SavedLines lines={record.chi_tiet} items={items} />
      <div className="actions">
        <Button onClick={changeActive}>
          {record.is_active ? "Ngừng dùng phiên bản" : "Kích hoạt phiên bản"}
        </Button>
        <Link to={`${base}/moi`} className="btn btn-secondary">
          Tạo phiên bản mới
        </Link>
      </div>
      <Notice>Nội dung BOM đã lưu bất biến. Thay đổi công thức bằng phiên bản mới.</Notice>
      <h3>Cấu trúc nhiều cấp</h3>
      <QueryState query={tree}>
        <BomTree nodes={tree.data?.data.children || []} items={items} />
      </QueryState>
    </div>
  );
}
function BomTree({ nodes, items }) {
  return (
    <ul className="tree">
      {nodes.map((node) => (
        <li key={node.mat_hang_id}>
          <strong>{itemName(items, node.mat_hang_id)}</strong> × {node.so_luong_tren_mot_don_vi_cha}
          {node.bom_id && <small className="muted"> · BOM #{node.bom_id}</small>}
          {node.children?.length > 0 && <BomTree nodes={node.children} items={items} />}
        </li>
      ))}
    </ul>
  );
}
