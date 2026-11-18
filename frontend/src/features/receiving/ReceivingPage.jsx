import { useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import {
  useCatalog,
  useChoices,
  useCollection,
  useDetail,
  useResource,
  useWrite,
} from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { dateTime, money, nullable } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import {
  DocumentLines,
  newLine,
  linePayload,
  SavedLines,
  statusFilter,
  dateFilters,
} from "../../components/ResourceFields.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
import { dateRangeError } from "../../components/filterFields.js";
import { prefillReceipt } from "./receiptPrefill.js";
import { receiptDraftsBySupplier } from "./receiptDrafts.js";
import styles from "./ReceivingPage.module.css";
const base = "/kho/phieu-nhap";
export function ReceivingPage() {
  const { id } = useParams();
  const [search] = useSearchParams();
  const requestId = search.get("yeu_cau_san_xuat_id");
  const shouldPrefill = id === "moi" && requestId !== null;
  const shortageQuery = useResource(API.shortages, {}, shouldPrefill);
  const shortages = shortageQuery.isFetching && !shortageQuery.isFetchedAfterMount
    ? { ...shortageQuery, isPending: true }
    : shortageQuery;
  const collection = useCollection(API.receipts, {
    sort: "-created_at",
    ncc_id: search.get("ncc_id") || "",
  });
  const detail = useDetail(API.receipts, id);
  const catalog = useCatalog();
  const suppliers = useChoices(API.suppliers);
  const items = catalog.data?.data || [];
  return (
    <>
      <PageHeader
        title="Phiếu nhập kho"
        subtitle="Phiếu nháp không cộng tồn. Chỉ hoàn tất nhập kho mới ghi sổ."
        action={
          <Link className="btn btn-primary" to={`${base}/moi`}>
            Tạo phiếu nhập
          </Link>
        }
      />
      <div className="stack">
        <Collection
          collection={collection}
          allowReset
          pageSizes={[20, 50, 100]}
          validate={dateRangeError}
          filters={[statusFilter(["nhap", "hoan_thanh"]), ...dateFilters]}
          columns={[
            {
              key: "ma_phieu_nhap",
              label: "Mã phiếu",
              render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_phieu_nhap}</Link>,
            },
            {
              key: "ncc_id",
              label: "Nhà cung cấp",
              render: (row) =>
                suppliers.data?.find((supplier) => supplier.id === row.ncc_id)?.ten_ncc ||
                `NCC #${row.ncc_id}`,
            },
            { key: "ngay_nhap", label: "Ngày nhập" },
            {
              key: "tong_tien",
              label: "Tổng tiền",
              numeric: true,
              render: (row) => money(row.tong_tien),
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
                <Link to={`${base}/${row.id}`}>
                  {row.trang_thai === "nhap" ? "Mở nháp" : "Xem"} →
                </Link>
              ),
            },
          ]}
        />
        <RecordPanel
          id={id}
          query={detail}
          base={base}
          title={id === "moi" ? "Tạo phiếu nhập" : "Chi tiết phiếu nhập"}
        >
          {(snapshot) => {
            const request = shouldPrefill && !shortages.isPending
              ? shortages.data?.data?.yeu_cau?.find((entry) => entry.id === Number(requestId))
              : undefined;
            const prefill = prefillReceipt(request, items);
            const editor = (
              <ReceiptEditor
                key={shouldPrefill ? requestId : undefined}
                snapshot={snapshot}
                items={items}
                suppliers={suppliers}
                prefill={prefill}
                prefillMissing={shouldPrefill && prefill === null}
              />
            );
            return (
              <QueryState query={catalog}>
                {shouldPrefill ? <QueryState query={shortages}>{editor}</QueryState> : editor}
              </QueryState>
            );
          }}
        </RecordPanel>
      </div>
    </>
  );
}
function ReceiptEditor({
  snapshot,
  items,
  suppliers,
  prefill,
  prefillMissing: initialPrefillMissing,
}) {
  const record = snapshot?.data;
  const editable = !record || record.trang_thai === "nhap";
  const navigate = useNavigate();
  const { confirm, notify } = useFeedback();
  const action = useWrite();
  const { save, busy, error } = useSave();
  const creating = useRef(false);
  const [creatingDrafts, setCreatingDrafts] = useState(false);
  const [creationError, setCreationError] = useState(null);
  const [savedDrafts, setSavedDrafts] = useState([]);
  const [uncertainDraft, setUncertainDraft] = useState(false);
  const initial = {
    ncc_id: String(record?.ncc_id || ""),
    ngay_nhap: record?.ngay_nhap ?? "",
    ghi_chu: record ? record.ghi_chu || "" : (prefill?.ghi_chu ?? ""),
  };
  const [values, setValues] = useState(initial);
  const [prefillMissing] = useState(initialPrefillMissing);
  const [lines, setLines] = useState(
    () =>
      record?.chi_tiet.map((line) =>
        newLine({
          ...line,
          mat_hang_id: String(line.mat_hang_id),
          so_luong: String(line.so_luong),
          don_gia_thuc: String(line.don_gia_thuc ?? 0),
        }),
      ) ||
      prefill?.lines || [newLine()],
  );
  const supplierOptions = [
    { value: "", label: "Chọn nhà cung cấp" },
    ...(suppliers.data ?? []).map((supplier) => ({
      value: String(supplier.id),
      label: `${supplier.ma_ncc} · ${supplier.ten_ncc}`,
    })),
  ];
  const supplierCount = new Set(lines.map((line) => line.ncc_id).filter(Boolean)).size;
  const dirty =
    JSON.stringify(values) !== JSON.stringify(initial) ||
    Boolean(
      record &&
      JSON.stringify(linePayload(lines, true)) !==
        JSON.stringify(
          record.chi_tiet.map(({ mat_hang_id, so_luong, don_gia_thuc }) => ({
            mat_hang_id,
            so_luong,
            don_gia_thuc,
          })),
        ),
    );
  async function createDrafts(fields) {
    if (creating.current || uncertainDraft) return;
    setCreationError(null);
    let bodies;
    try {
      bodies = receiptDraftsBySupplier(lines, fields);
    } catch (failure) {
      setCreationError(failure);
      return;
    }

    creating.current = true;
    setCreatingDrafts(true);
    const created = [];
    try {
      for (const body of bodies) {
        const { data } = await action.mutateAsync({ path: API.receipts, body, versioned: false });
        created.push({ id: data.id, code: data.ma_phieu_nhap, supplierId: body.ncc_id });
      }
      const total = savedDrafts.length + created.length;
      notify(`Đã lưu ${total} phiếu nhập nháp.`);
      navigate(total === 1 ? `${base}/${created[0].id}` : base);
    } catch (failure) {
      const savedSuppliers = new Set(created.map((draft) => draft.supplierId));
      setSavedDrafts((previous) => [...previous, ...created]);
      setLines((previous) => previous.filter((line) => !savedSuppliers.has(Number(line.ncc_id))));
      setCreationError(failure);
      setUncertainDraft(!failure.status || failure.status === 408 || failure.status >= 500);
    } finally {
      creating.current = false;
      setCreatingDrafts(false);
    }
  }

  function submit(event) {
    event.preventDefault();
    const fields = { ngay_nhap: values.ngay_nhap, ghi_chu: nullable(values.ghi_chu) };
    if (!record) return createDrafts(fields);

    const body = {
      ncc_id: Number(values.ncc_id),
      ...fields,
      chi_tiet: linePayload(lines, true),
    };
    save(
      {
        path: `${API.receipts}/${record.id}`,
        method: "patch",
        body,
        etag: snapshot.etag,
      },
      (result) => navigate(`${base}/${result.data.id}`),
    );
  }
  function confirmAction(remove = false) {
    confirm({
      title: remove ? "Xóa phiếu nhập nháp" : "Hoàn tất nhập kho",
      description: `${record.ma_phieu_nhap} · ngày nhập ${record.ngay_nhap}.`,
      content: <SavedLines lines={record.chi_tiet} items={items} prices />,
      danger: remove,
      impact: remove
        ? "Xóa bản nháp, không thay đổi tồn kho."
        : "Cộng số lượng từng mặt hàng vào kho và ghi giao dịch một lần. Sau khi xác nhận, phiếu không thể chỉnh sửa.",
      onConfirm: async () => {
        const result = await action.mutateAsync({
          path: `${API.receipts}/${record.id}${remove ? "" : "/hoan_tat"}`,
          method: remove ? "delete" : "post",
          body: remove ? null : {},
          etag: snapshot.etag,
        });
        notify(
          remove
            ? "Đã xóa phiếu nhập nháp."
            : `Đã hoàn tất nhập kho.${result.data?.giao_dich_kho_ids?.length ? ` Giao dịch nhập gốc: ${result.data.giao_dich_kho_ids.join(", ")}.` : ""}`,
        );
        if (remove) navigate(base);
      },
    });
  }
  const saveActions = (
    <div className="actions actions-end">
      {!record && supplierCount > 1 && (
        <span className="muted">Sẽ tạo {supplierCount} phiếu nháp, mỗi nhà cung cấp một phiếu.</span>
      )}
      <span className="muted">
        Tạm tính:{" "}
        {money(
          lines.reduce((sum, line) => sum + Number(line.so_luong) * Number(line.don_gia_thuc), 0),
        )}
      </span>
      <Button type="submit" disabled={busy || creatingDrafts || uncertainDraft}>
        {creatingDrafts ? "Đang lưu…" : "Lưu nháp"}
      </Button>
    </div>
  );
  return (
    <div className="stack">
      {record && (
        <div className="actions">
          <h3>{record.ma_phieu_nhap}</h3>
          <Badge status={record.trang_thai} />
        </div>
      )}
      <ErrorNotice error={record ? error : creationError} />
      {savedDrafts.length > 0 && (
        <Notice>
          Phiếu nháp đã lưu{" "}
          {savedDrafts.map((draft, index) => (
            <span key={draft.id}>
              {index > 0 && ", "}
              <Link to={`${base}/${draft.id}`}>{draft.code || `#${draft.id}`}</Link>
            </span>
          ))}
          . Các dòng bên dưới chưa được xác nhận lưu.
        </Notice>
      )}
      {uncertainDraft && (
        <Notice tone="warning">
          Chưa xác định được kết quả lưu. Anh hãy kiểm tra{" "}
          <Link to={base}>danh sách phiếu nhập</Link> trước khi lập lại các dòng chưa xác nhận.
        </Notice>
      )}
      {editable ? (
        <QueryState query={suppliers}>
          <form className={record ? undefined : styles.createForm} onSubmit={submit}>
            <fieldset className={styles.formFields} disabled={creatingDrafts}>
              <div className="stack">
                {prefillMissing && (
                  <Notice>Yêu cầu này không còn linh kiện thiếu. Phiếu nhập được tạo trống.</Notice>
                )}
                <div className={record ? "form-grid" : styles.metadata}>
                  {record && (
                    <Field
                      as="select"
                      label="Nhà cung cấp"
                      required
                      options={supplierOptions}
                      value={values.ncc_id}
                      onChange={(event) => setValues({ ...values, ncc_id: event.target.value })}
                    />
                  )}
                  <Field
                    label="Ngày nhập"
                    type="date"
                    name="ngay_nhap"
                    required
                    value={values.ngay_nhap}
                    onChange={(event) => setValues({ ...values, ngay_nhap: event.target.value })}
                  />
                  <div className={record ? styles.fullWidth : styles.note}>
                    <Field
                      as="textarea"
                      rows={record ? 2 : 1}
                      label="Ghi chú"
                      value={values.ghi_chu}
                      onChange={(event) => setValues({ ...values, ghi_chu: event.target.value })}
                    />
                  </div>
                </div>
                <DocumentLines
                  lines={lines}
                  onChange={setLines}
                  items={items}
                  prices
                  types={["linh_kien"]}
                  allowDuplicateItems={!record}
                  afterAdd={!record ? saveActions : undefined}
                  columnAfterItem={
                    record
                      ? undefined
                      : {
                          label: "Nhà cung cấp",
                          render: (line, index, update) => (
                            <select
                              aria-label={`Nhà cung cấp dòng ${index + 1}`}
                              required
                              value={line.ncc_id ?? ""}
                              onChange={(event) => update({ ncc_id: event.target.value })}
                            >
                              {supplierOptions.map(({ value, label }) => (
                                <option key={value} value={value}>
                                  {label}
                                </option>
                              ))}
                            </select>
                          ),
                        }
                  }
                />
                {record && saveActions}
              </div>
            </fieldset>
          </form>
        </QueryState>
      ) : (
        <>
          <InfoGrid
            entries={[
              ["Ngày nhập", record.ngay_nhap],
              ["Người lập", `Nhân viên #${record.nhan_vien_id}`],
              ["Tổng tiền", money(record.tong_tien)],
              ["Tạo lúc", dateTime(record.created_at)],
              ["Ghi chú", record.ghi_chu],
            ]}
          />
          <SavedLines lines={record.chi_tiet} items={items} prices />
          <div className="actions">
            <Link className="btn btn-primary" to={`/kho/dieu-chinh/moi?phieu_nhap_id=${record.id}`}>
              Tạo phiếu điều chỉnh
            </Link>
          </div>
        </>
      )}
      {record && editable && (
        <div className="actions actions-end">
          <Button
            variant="secondary"
            reason={dirty ? "Lưu hoặc tải lại bản nháp trước khi xóa." : undefined}
            onClick={() => confirmAction(true)}
          >
            Xóa nháp
          </Button>
          <Button
            reason={dirty ? "Lưu hoặc tải lại bản nháp trước khi hoàn tất." : undefined}
            onClick={() => confirmAction()}
          >
            Hoàn tất nhập kho
          </Button>
        </div>
      )}
    </div>
  );
}
