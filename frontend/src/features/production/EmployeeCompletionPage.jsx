import { useEffect, useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useCollection, useDetail, useWrite } from "../../lib/api/useResources.js";
import { dateTime, itemDisplayName, itemName, number } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { statusFilter, dateFilters } from "../../components/ResourceFields.jsx";
import { dateRangeError } from "../../components/filterFields.js";
import { ErrorNotice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
import { canSendCompletion, completionConfirmEntries, completionSendLabel } from "./completionForm.js";

function parseCompletionParams(searchParams) {
  const params = {
    page: searchParams.get("page") ? Math.max(1, Number(searchParams.get("page"))) : 1,
    page_size: 20,
  };
  const matHangId = searchParams.get("mat_hang_id");
  if (matHangId) params.mat_hang_id = Number(matHangId);
  if (searchParams.get("trang_thai")) params.trang_thai = searchParams.get("trang_thai");
  if (searchParams.get("loai_yeu_cau")) params.loai_yeu_cau = searchParams.get("loai_yeu_cau");
  if (searchParams.get("tu_ngay")) params.tu_ngay = searchParams.get("tu_ngay");
  if (searchParams.get("den_ngay")) params.den_ngay = searchParams.get("den_ngay");
  return params;
}

export function EmployeeCompletionPage() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const catalog = useCatalog();
  const items = catalog.data?.data || [];
  const detail = useDetail(API.completions, id);

  const initialFilters = useMemo(() => parseCompletionParams(searchParams), []);

  const collection = useCollection(
    `${API.completions}/cua_toi`,
    initialFilters,
  );

  useEffect(() => {
    const desired = parseCompletionParams(searchParams);
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
    for (const [k, v] of Object.entries(next)) {
      if (k === "page" || k === "page_size" || k === "sort") continue;
      if (v !== undefined && v !== null && v !== "") {
        nextSearchParams.set(k, String(v));
      }
    }
    // Filter changes ALWAYS reset page to 1
    if (nextSearchParams.toString() !== searchParams.toString()) {
      setSearchParams(nextSearchParams);
    }
  }

  function handleSetPage(page) {
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
    setPage: handleSetPage,
  }), [collection, searchParams]);

  const searchString = searchParams.toString() ? `?${searchParams.toString()}` : "";
  const base = `/nv/chung-tu-hoan-thanh${searchString}`;

  return (
    <>
      <PageHeader
        title="Chứng từ hoàn thành"
      />

      <Collection
        collection={wrappedCollection}
        title="Danh sách chứng từ hoàn thành"
        search={false}
        validate={dateRangeError}
        cycleFilters={true}
        syncDraftWithParams={true}
        filters={[
          statusFilter(["nhap", "cho_duyet", "da_duyet", "tu_choi"]),
          ...dateFilters,
        ]}
        columns={[
          {
            key: "ma_phieu",
            label: "Mã chứng từ",
            render: (row) => <span>{row.ma_phieu}</span>,
          },
          {
            key: "ma_yeu_cau_san_xuat",
            label: "Mã YCSX",
            render: (row) => row.ma_yeu_cau_san_xuat || `YCSX #${row.yeu_cau_san_xuat_id}`,
          },
          {
            key: "mat_hang_id",
            label: "Thành phẩm",
            render: (row) => itemDisplayName(items, row.mat_hang_id) || itemName(items, row.mat_hang_id),
          },
          {
            key: "so_luong_hoan_thanh",
            label: "Số lượng hoàn thành",
            numeric: true,
            render: (row) => number(row.so_luong_hoan_thanh),
          },
          {
            key: "finish_time",
            label: "Thời điểm hoàn thành",
            render: (row) => (row.finish_time ? dateTime(row.finish_time) : "—"),
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
              <Link to={`/nv/chung-tu-hoan-thanh/${row.id}${searchString}`} className="btn btn-secondary btn-sm">
                Xem chi tiết
              </Link>
            ),
          },
        ]}
      />

      <RecordPanel
        id={id}
        query={detail}
        base={base}
        title="Chi tiết chứng từ hoàn thành"
      >
        {(snapshot) => (
          <QueryState query={catalog}>
            <EmployeeCompletionDetail
              snapshot={snapshot}
              items={items}
            />
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}

function EmployeeCompletionDetail({ snapshot, items }) {
  const completion = snapshot?.data;
  const etag = snapshot?.etag;
  const mutation = useWrite();
  const { user } = useAuth();
  const { confirm, notify } = useFeedback();

  const sourceQuery = useDetail(API.requests, completion?.yeu_cau_san_xuat_id);
  const sourceRecord = sourceQuery.data?.data?.id === completion?.yeu_cau_san_xuat_id ? sourceQuery.data?.data : null;

  if (!completion) return null;

  const productItem = items?.find((item) => Number(item.id) === Number(sourceRecord?.mat_hang_id || completion.mat_hang_id));
  const productText = productItem?.ma_mat_hang
    ? `${productItem.ten_mat_hang} — ${productItem.ma_mat_hang}`
    : (productItem?.ten_mat_hang || (completion.mat_hang_id ? `Mặt hàng #${completion.mat_hang_id}` : "—"));
  const sourceText = sourceRecord?.ma_yeu_cau_san_xuat || (sourceQuery.isPending ? "Đang tải…" : (completion.yeu_cau_san_xuat_id ? `YCSX #${completion.yeu_cau_san_xuat_id}` : "—"));

  const canSend = Boolean(sourceRecord && canSendCompletion(sourceRecord, completion, false, user?.id));

  function sendCompletion() {
    confirm({
      title: completion.trang_thai === "tu_choi" ? "Gửi lại chứng từ hoàn thành" : "Gửi chứng từ hoàn thành",
      description: completion.ma_phieu,
      content: (
        <InfoGrid
          entries={completionConfirmEntries(completion, sourceRecord, items, true)}
        />
      ),
      hideImpact: true,
      onConfirm: async () => {
        await mutation.mutateAsync({
          path: `${API.completions}/${completion.id}/gui`,
          method: "post",
          body: {},
          etag,
        });
        notify(completion.trang_thai === "tu_choi" ? "Đã gửi lại chứng từ hoàn thành." : "Đã gửi chứng từ hoàn thành.");
      },
    });
  }

  return (
    <div className="stack">
      {sourceQuery.isError && <ErrorNotice error={sourceQuery.error} />}
      <h3>{completion.ma_phieu}</h3>
      <InfoGrid
        entries={[
          ["Mã chứng từ", completion.ma_phieu],
          ["Trạng thái", <Badge status={completion.trang_thai} />],
          ["Yêu cầu sản xuất", sourceText],
          ["Thành phẩm", productText],
          ["Số lượng hoàn thành", number(completion.so_luong_hoan_thanh)],
          ["Thời điểm hoàn thành", completion.finish_time ? dateTime(completion.finish_time) : "—"],
          ["Thời điểm lập", dateTime(completion.created_at)],
          ...(completion.xu_ly_at ? [["Thời điểm xử lý", dateTime(completion.xu_ly_at)]] : []),
          ...(completion.ly_do_tu_choi ? [["Lý do từ chối", completion.ly_do_tu_choi]] : []),
        ]}
      />
      {canSend && (
        <div className="actions actions-end">
          <Button disabled={mutation.isPending} onClick={sendCompletion}>
            {completionSendLabel(completion)}
          </Button>
        </div>
      )}
    </div>
  );
}
