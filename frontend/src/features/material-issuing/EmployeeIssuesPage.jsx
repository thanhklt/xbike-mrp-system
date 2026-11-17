import { useEffect, useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useCollection, useDetail } from "../../lib/api/useResources.js";
import { dateTime, itemDisplayName, money, number, unitLabel } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { ApprovalActions } from "../../components/ApprovalActions.jsx";
import { SavedLines, statusFilter, dateFilters } from "../../components/ResourceFields.jsx";
import { dateRangeError } from "../../components/filterFields.js";
import { Notice, QueryState } from "../../components/QueryState.jsx";
import { issueTypeLabel } from "./issueForm.js";

function parseIssueParams(searchParams) {
  const params = {
    page: searchParams.get("page") ? Math.max(1, Number(searchParams.get("page"))) : 1,
    page_size: 20,
    loai_phieu: searchParams.get("tab") === "xuat_thanh_pham" ? "xuat_thanh_pham" : "xuat_linh_kien",
  };
  const requestId = searchParams.get("yeu_cau_san_xuat_id");
  if (requestId) params.yeu_cau_san_xuat_id = Number(requestId);
  if (searchParams.get("q")) params.q = searchParams.get("q");
  if (searchParams.get("trang_thai")) params.trang_thai = searchParams.get("trang_thai");
  if (searchParams.get("tu_ngay")) params.tu_ngay = searchParams.get("tu_ngay");
  if (searchParams.get("den_ngay")) params.den_ngay = searchParams.get("den_ngay");
  return params;
}

export function EmployeeIssuesPage() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") === "xuat_thanh_pham" ? "xuat_thanh_pham" : "xuat_linh_kien";
  const requestIdParam = searchParams.get("yeu_cau_san_xuat_id");

  const catalog = useCatalog();
  const items = catalog.data?.data || [];
  const detail = useDetail(API.issues, id);

  const initialFilters = useMemo(() => parseIssueParams(searchParams), []);
  const collection = useCollection(
    `${API.issues}/cua_toi`,
    initialFilters,
  );

  useEffect(() => {
    const desired = parseIssueParams(searchParams);
    const keys = new Set([...Object.keys(desired), ...Object.keys(collection.params)]);
    let changed = false;
    for (const k of keys) {
      if (k === "page_size") continue;
      if (desired[k] !== collection.params[k]) {
        changed = true;
        break;
      }
    }
    if (changed) {
      collection.reset(desired);
    }
  }, [searchParams]);

  function applyFilters(next) {
    const nextSearchParams = new URLSearchParams();
    if (activeTab === "xuat_thanh_pham") nextSearchParams.set("tab", "xuat_thanh_pham");
    if (requestIdParam) nextSearchParams.set("yeu_cau_san_xuat_id", requestIdParam);
    for (const [k, v] of Object.entries(next)) {
      if (k === "page" || k === "page_size" || k === "tab" || k === "loai_phieu" || k === "yeu_cau_san_xuat_id") continue;
      if (v !== undefined && v !== null && v !== "") {
        nextSearchParams.set(k, String(v));
      }
    }
    // Filter changes ALWAYS reset page to 1
    if (nextSearchParams.toString() !== searchParams.toString()) {
      setSearchParams(nextSearchParams);
    }
  }

  function setPage(page) {
    const nextSearchParams = new URLSearchParams(searchParams);
    if (page > 1) {
      nextSearchParams.set("page", String(page));
    } else {
      nextSearchParams.delete("page");
    }
    if (nextSearchParams.toString() !== searchParams.toString()) {
      setSearchParams(nextSearchParams);
    }
  }

  const wrappedCollection = useMemo(() => ({
    ...collection,
    filter: applyFilters,
    reset: applyFilters,
    setPage,
  }), [collection, searchParams, activeTab, requestIdParam]);

  const searchString = searchParams.toString() ? `?${searchParams.toString()}` : "";
  const backUrl = `/nv/phieu-xuat${searchString}`;

  function handleTabChange(tab) {
    if (tab === activeTab) return;
    const nextSearchParams = new URLSearchParams(searchParams);
    if (tab === "xuat_thanh_pham") {
      nextSearchParams.set("tab", "xuat_thanh_pham");
    } else {
      nextSearchParams.delete("tab");
    }
    nextSearchParams.delete("page");
    setSearchParams(nextSearchParams);
  }

  return (
    <>
      <PageHeader
        title="Phiếu xuất"
      />

      <div className="tab-group" role="tablist" aria-label="Loại phiếu xuất" style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "xuat_linh_kien"}
          aria-controls="panel-xuat-linh-kien"
          id="tab-xuat-linh-kien"
          className={`btn ${activeTab === "xuat_linh_kien" ? "btn-primary" : "btn-secondary"}`}
          onClick={() => handleTabChange("xuat_linh_kien")}
          onKeyDown={(e) => {
            if (e.key === "ArrowRight" || e.key === "ArrowDown") {
              e.preventDefault();
              handleTabChange("xuat_thanh_pham");
              document.getElementById("tab-xuat-thanh-pham")?.focus();
            }
          }}
        >
          Xuất linh kiện
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "xuat_thanh_pham"}
          aria-controls="panel-xuat-thanh-pham"
          id="tab-xuat-thanh-pham"
          className={`btn ${activeTab === "xuat_thanh_pham" ? "btn-primary" : "btn-secondary"}`}
          onClick={() => handleTabChange("xuat_thanh_pham")}
          onKeyDown={(e) => {
            if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
              e.preventDefault();
              handleTabChange("xuat_linh_kien");
              document.getElementById("tab-xuat-linh-kien")?.focus();
            }
          }}
        >
          Xuất thành phẩm
        </button>
      </div>

      <div
        id={activeTab === "xuat_linh_kien" ? "panel-xuat-linh-kien" : "panel-xuat-thanh-pham"}
        role="tabpanel"
        aria-labelledby={activeTab === "xuat_linh_kien" ? "tab-xuat-linh-kien" : "tab-xuat-thanh-pham"}
      >
        <Collection
          collection={wrappedCollection}
          title={activeTab === "xuat_linh_kien" ? "Danh sách phiếu xuất linh kiện" : "Danh sách phiếu xuất thành phẩm"}
          searchPlaceholder="Tìm mã phiếu xuất…"
          validate={dateRangeError}
          cycleFilters={true}
          syncDraftWithParams={true}
          filters={[
            statusFilter(["nhap", "cho_duyet", "da_duyet", "tu_choi"]),
            ...dateFilters,
          ]}
          columns={[
            {
              key: "ma_phieu_xuat",
              label: "Mã phiếu",
              render: (row) => <span>{row.ma_phieu_xuat}</span>,
            },
            {
              key: "yeu_cau_san_xuat_id",
              label: "Mã YCSX",
              render: (row) => row.ma_yeu_cau_san_xuat || (row.yeu_cau_san_xuat_id ? `YCSX #${row.yeu_cau_san_xuat_id}` : "—"),
            },
            {
              key: "chi_tiet",
              label: activeTab === "xuat_linh_kien" ? "Mặt hàng" : "Thành phẩm",
              render: (row) =>
                row.chi_tiet.map((line) => itemDisplayName(items, line.mat_hang_id)).filter(Boolean).join(", ") || "—",
            },
            {
              key: "created_at",
              label: "Thời gian lập",
              render: (row) => dateTime(row.created_at),
            },
            {
              key: "trang_thai",
              label: "Trạng thái",
              render: (row) => <Badge status={row.trang_thai} />,
            },
            {
              key: "action",
              label: "Thao tác",
              render: (row) => (
                <Link to={`/nv/phieu-xuat/${row.id}${searchString}`} className="btn btn-secondary btn-sm">
                  Xem chi tiết
                </Link>
              ),
            },
          ]}
        />
      </div>

      <RecordPanel
        id={id}
        query={detail}
        base={backUrl}
        title="Chi tiết phiếu xuất"
      >
        {(snapshot) => (
          <QueryState query={catalog}>
            <EmployeeIssueDetail
              snapshot={snapshot}
              items={items}
              base={backUrl}
            />
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}

function EmployeeIssueDetail({ snapshot, items }) {
  const record = snapshot?.data;
  if (!record) return null;

  const source = useDetail(API.requests, record.yeu_cau_san_xuat_id);
  const type = record.loai_phieu;
  const firstLine = record.chi_tiet?.[0];
  const firstItem = items.find((item) => item.id === firstLine?.mat_hang_id);

  const matchedSource = source.data?.data?.id === record.yeu_cau_san_xuat_id ? source.data?.data : null;
  const sourceText = matchedSource?.ma_yeu_cau_san_xuat || (source.isPending ? "Đang tải…" : (source.isError ? "—" : `YCSX #${record.yeu_cau_san_xuat_id}`));

  return (
    <div className="stack">
      {source.isError && <Notice>Không tải được thông tin yêu cầu sản xuất liên quan.</Notice>}
      <h3>{record.ma_phieu_xuat}</h3>
      <InfoGrid
        entries={[
          ["Mã phiếu xuất", record.ma_phieu_xuat],
          ["Trạng thái", <Badge status={record.trang_thai} />],
          [
            "Yêu cầu sản xuất",
            sourceText,
          ],
          ["Ngày lập", dateTime(record.created_at)],
          [
            type === "xuat_linh_kien" ? "Mặt hàng đầu" : "Mã thành phẩm",
            firstItem ? `${firstItem.ten_mat_hang} — ${firstItem.ma_mat_hang || firstItem.sku}` : "—",
          ],
          [
            "Số lượng xuất",
            record.chi_tiet.length === 1
              ? `${number(firstLine?.so_luong)} ${unitLabel(firstItem?.don_vi_tinh) || ""}`
              : `${record.chi_tiet.length} dòng mặt hàng`,
          ],
          ["Loại phiếu", issueTypeLabel(type)],
          ["Tổng tiền server chốt", money(record.tong_tien)],
          ...(record.ly_do_tu_choi ? [["Lý do từ chối", record.ly_do_tu_choi]] : []),
        ]}
      />
      <SavedLines lines={record.chi_tiet} items={items} prices />
      {matchedSource && (
        <QueryState query={source}>
          <ApprovalActions
            kind="issue"
            path={API.issues}
            snapshot={snapshot}
            items={items}
            assignedId={matchedSource.nhan_vien_duoc_giao_id}
          />
        </QueryState>
      )}
    </div>
  );
}
