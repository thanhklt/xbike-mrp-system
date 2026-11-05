import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useChoices, useCollection, useDetail } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { money, dateTime } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { documentPermissions } from "../auth/permissions.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Field } from "../../components/Field.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { ApprovalActions } from "../../components/ApprovalActions.jsx";
import {
  DocumentLines,
  SavedLines,
  newLine,
  linePayload,
  statusFilter,
  dateFilters,
} from "../../components/ResourceFields.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
export function MaterialIssuingPage({ issueType }) {
  const { id } = useParams();
  const { user } = useAuth();
  const manager = user.ma_vai_tro === "quan_ly";
  const base = manager
    ? "/kho/phieu-xuat"
    : issueType === "xuat_thanh_pham"
      ? "/nv/xuat-tp"
      : "/nv/xuat-nvl";
  const collection = useCollection(API.issues, {
    sort: "-created_at",
    ...(issueType ? { loai_phieu: issueType } : {}),
  });
  const detail = useDetail(API.issues, id);
  const catalog = useCatalog();
  return (
    <>
      <PageHeader
        title={
          manager
            ? "Phiếu xuất kho"
            : issueType === "xuat_thanh_pham"
              ? "Phiếu xuất thành phẩm"
              : "Phiếu xuất NVL / BTP"
        }
        subtitle={
          manager
            ? "Lập, gửi và duyệt xuất vật tư hoặc thành phẩm. Chỉ duyệt mới trừ tồn."
            : "Chỉ xem phiếu liên quan đến công việc được giao. Quản lý kho lập và duyệt phiếu."
        }
        action={
          manager && (
            <Link className="btn btn-primary" to={`${base}/moi`}>
              Tạo phiếu xuất
            </Link>
          )
        }
      />
      <Collection
        collection={collection}
        filters={[
          statusFilter(["nhap", "cho_duyet", "da_duyet", "tu_choi"]),
          ...(!issueType
            ? [
                {
                  name: "loai_phieu",
                  label: "Loại phiếu",
                  as: "select",
                  options: [
                    { value: "", label: "Tất cả" },
                    { value: "xuat_vat_tu", label: "Xuất vật tư" },
                    { value: "xuat_thanh_pham", label: "Xuất thành phẩm" },
                  ],
                },
              ]
            : []),
          ...dateFilters,
        ]}
        columns={[
          {
            key: "ma_phieu_xuat",
            label: "Mã phiếu",
            render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_phieu_xuat}</Link>,
          },
          {
            key: "loai_phieu",
            label: "Loại",
            render: (row) => (row.loai_phieu === "xuat_vat_tu" ? "Vật tư / BTP" : "Thành phẩm"),
          },
          {
            key: "source",
            label: "Tham chiếu",
            render: (row) =>
              row.lenh_san_xuat_id
                ? `LSX #${row.lenh_san_xuat_id}`
                : `YCSX #${row.yeu_cau_san_xuat_id}`,
          },
          { key: "created_at", label: "Tạo lúc", render: (row) => dateTime(row.created_at) },
          {
            key: "trang_thai",
            label: "Trạng thái",
            render: (row) => <Badge status={row.trang_thai} />,
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
        title={id === "moi" ? "Tạo phiếu xuất" : "Chi tiết phiếu xuất"}
      >
        {(snapshot) => (
          <QueryState query={catalog}>
            <IssueEditor snapshot={snapshot} items={catalog.data?.data || []} base={base} />
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}
function IssueEditor({ snapshot, items, base }) {
  const record = snapshot?.data;
  const { user } = useAuth();
  const permissions = documentPermissions("issue", user.ma_vai_tro, record, user.id);
  const [search] = useSearchParams();
  const [type, setType] = useState(record?.loai_phieu || search.get("loai_phieu") || "xuat_vat_tu");
  const [sourceId, setSourceId] = useState(
    String(
      record?.lenh_san_xuat_id ||
        record?.yeu_cau_san_xuat_id ||
        search.get("lenh_san_xuat_id") ||
        search.get("yeu_cau_san_xuat_id") ||
        "",
    ),
  );
  const [lines, setLines] = useState(
    () =>
      record?.chi_tiet.map((line) =>
        newLine({
          ...line,
          mat_hang_id: String(line.mat_hang_id),
          so_luong: String(line.so_luong),
        }),
      ) || [newLine()],
  );
  const sourcePath = type === "xuat_vat_tu" ? API.orders : API.requests;
  const sources = useChoices(sourcePath, {}, !record && permissions.create);
  const { save, busy, error } = useSave();
  const navigate = useNavigate();
  const dirty = Boolean(
    record &&
    JSON.stringify(linePayload(lines)) !==
      JSON.stringify(
        record.chi_tiet.map(({ mat_hang_id, so_luong }) => ({ mat_hang_id, so_luong })),
      ),
  );
  const editable = record ? permissions.edit : permissions.create;
  function submit(event) {
    event.preventDefault();
    const body = record
      ? { chi_tiet: linePayload(lines) }
      : {
          loai_phieu: type,
          ...(type === "xuat_vat_tu"
            ? { lenh_san_xuat_id: Number(sourceId) }
            : { yeu_cau_san_xuat_id: Number(sourceId) }),
          chi_tiet: linePayload(lines),
        };
    save(
      {
        path: record ? `${API.issues}/${record.id}` : API.issues,
        method: record ? "patch" : "post",
        body,
        versioned: Boolean(record),
        etag: snapshot?.etag,
      },
      (result) => navigate(`${base}/${result.data.id}`),
    );
  }
  if (!record && !permissions.create) return <Notice>Bạn không có quyền lập phiếu xuất.</Notice>;
  return (
    <div className="stack">
      {record && (
        <>
          <div className="actions">
            <h3>{record.ma_phieu_xuat}</h3>
            <Badge status={record.trang_thai} />
          </div>
          <InfoGrid
            entries={[
              ["Người lập", `Nhân viên #${record.nhan_vien_id}`],
              ["Tạo lúc", dateTime(record.created_at)],
              ["Loại phiếu", type === "xuat_vat_tu" ? "Xuất vật tư / BTP" : "Xuất thành phẩm"],
              ["Nguồn", `${type === "xuat_vat_tu" ? "Lệnh" : "Yêu cầu"} #${sourceId}`],
              ["Tổng tiền server chốt", money(record.tong_tien)],
            ]}
          />
        </>
      )}
      <ErrorNotice error={error} />
      {editable ? (
        <form className="stack" onSubmit={submit}>
          {!record && (
            <>
              <Field
                as="select"
                label="Loại phiếu"
                value={type}
                onChange={(event) => {
                  setType(event.target.value);
                  setSourceId("");
                  setLines([newLine()]);
                }}
              >
                <option value="xuat_vat_tu">Xuất vật tư / BTP</option>
                <option value="xuat_thanh_pham">Xuất thành phẩm</option>
              </Field>
              <QueryState query={sources}>
                <Field
                  as="select"
                  label={type === "xuat_vat_tu" ? "Lệnh sản xuất" : "Yêu cầu thành phẩm"}
                  required
                  value={sourceId}
                  onChange={(event) => setSourceId(event.target.value)}
                >
                  <option value="">Chọn nguồn</option>
                  {sources.data
                    ?.filter((source) => ["da_gui", "dang_thuc_hien"].includes(source.trang_thai))
                    .map((source) => (
                      <option key={source.id} value={source.id}>
                        {source.ma_lenh_san_xuat || source.ma_yeu_cau_san_xuat} · {source.so_luong}
                      </option>
                    ))}
                </Field>
              </QueryState>
            </>
          )}
          <DocumentLines
            lines={lines}
            onChange={setLines}
            items={items}
            types={
              type === "xuat_vat_tu"
                ? ["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham"]
                : ["thanh_pham"]
            }
          />
          <div className="actions actions-end">
            <Button type="submit" disabled={busy}>
              Lưu nháp
            </Button>
          </div>
        </form>
      ) : (
        <SavedLines lines={record.chi_tiet} items={items} prices />
      )}
      <Notice>
        Gửi duyệt chưa trừ tồn. Backend kiểm tra lại nhu cầu và tồn khi duyệt, đồng thời chốt giá từ
        mặt hàng. Không nhập đơn giá xuất.
      </Notice>
      {record && (
        <ApprovalActions
          kind="issue"
          path={API.issues}
          base={base}
          snapshot={snapshot}
          items={items}
          dirty={dirty}
        />
      )}
    </div>
  );
}
