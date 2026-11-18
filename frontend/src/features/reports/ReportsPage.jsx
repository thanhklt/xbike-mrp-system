import { useState } from "react";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Card } from "../../components/Card.jsx";
import { Field } from "../../components/Field.jsx";
import { Button } from "../../components/Button.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { QueryState } from "../../components/QueryState.jsx";
import { API } from "../../lib/api/endpoints.js";
import { useChoices, useResource } from "../../lib/api/useResources.js";
import { ITEM_LABELS, number, unitLabel } from "../../lib/format.js";
import {
  defaultReportForm,
  periodLabel,
  REPORT_ITEM_TYPES,
  reportQuery,
} from "./inventoryReport.js";

// UC-41 Xem báo cáo nhập-xuất-tồn — Main 1–4; R1–R5, A1–A3 (specs/use_cases/reporting/UC-41.md)
export function ReportsPage() {
  const [form, setForm] = useState(defaultReportForm);
  const [submitted, setSubmitted] = useState(null);
  const query = useResource(API.inventoryReport, submitted ?? {}, submitted !== null);
  const choices = useChoices(API.items);
  const report = query.data?.data;

  function change(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  }

  function submit(event) {
    event.preventDefault();
    const params = reportQuery(form);
    if (JSON.stringify(params) === JSON.stringify(submitted)) query.refetch();
    else setSubmitted(params);
  }

  return (
    <>
      <PageHeader
        title="Báo cáo nhập – xuất – tồn"
        subtitle="Chỉ tính chứng từ đã ghi nhận vào kho: phiếu nhập hoàn tất, phiếu xuất đã duyệt, chứng từ hoàn thành đã duyệt. Kỳ tính theo giờ Việt Nam."
      />
      <Card title="Kỳ thống kê">
        <form className="filters" onSubmit={submit}>
          <Field as="select" label="Kỳ thống kê" name="ky" value={form.ky} onChange={change}>
            <option value="thang">Tháng</option>
            <option value="quy">Quý</option>
            <option value="nam">Năm</option>
          </Field>
          <Field
            label="Năm"
            type="number"
            name="nam"
            value={form.nam}
            onChange={change}
            min="2"
            max="9998"
            required
          />
          {form.ky === "thang" && (
            <Field
              label="Tháng"
              type="number"
              name="thang"
              min="1"
              max="12"
              value={form.thang}
              onChange={change}
              required
            />
          )}
          {form.ky === "quy" && (
            <Field label="Quý" as="select" name="quy" value={form.quy} onChange={change}>
              <option>1</option>
              <option>2</option>
              <option>3</option>
              <option>4</option>
            </Field>
          )}
          <Field
            label="Loại mặt hàng"
            as="select"
            name="loai_mat_hang"
            value={form.loai_mat_hang}
            onChange={change}
            options={[{ value: "", label: "Tất cả" }, ...REPORT_ITEM_TYPES]}
          />
          <QueryState query={choices}>
            <Field
              label="Mặt hàng"
              as="select"
              name="mat_hang_id"
              value={form.mat_hang_id}
              onChange={change}
            >
              <option value="">Tất cả</option>
              {(choices.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.ma_mat_hang} · {item.ten_mat_hang}
                </option>
              ))}
            </Field>
          </QueryState>
          <div className="filter-actions">
            <Button type="submit" disabled={query.isFetching}>
              Xem báo cáo
            </Button>
            <Button variant="secondary" onClick={() => setForm(defaultReportForm())}>
              Xóa lọc
            </Button>
          </div>
        </form>
      </Card>
      <Card
        title={submitted ? periodLabel(report ?? submitted) : "Nhập – xuất – tồn theo mặt hàng"}
      >
        {submitted ? (
          <QueryState query={query}>
            <DataTable
              rows={(report?.mat_hang ?? []).map((row) => ({ ...row, id: row.mat_hang_id }))}
              empty="Không có mặt hàng thỏa bộ lọc."
              columns={[
                { key: "ma_mat_hang", label: "Mã mặt hàng" },
                { key: "ten_mat_hang", label: "Mặt hàng" },
                {
                  key: "loai_mat_hang",
                  label: "Loại",
                  render: (row) => ITEM_LABELS[row.loai_mat_hang],
                },
                { key: "don_vi_tinh", label: "ĐVT", render: (row) => unitLabel(row.don_vi_tinh) },
                {
                  key: "ton_dau_ky",
                  label: "Tồn đầu kỳ",
                  numeric: true,
                  render: (row) => number(row.ton_dau_ky),
                },
                {
                  key: "nhap_trong_ky",
                  label: "Nhập",
                  numeric: true,
                  render: (row) => number(row.nhap_trong_ky),
                },
                {
                  key: "xuat_trong_ky",
                  label: "Xuất",
                  numeric: true,
                  render: (row) => number(row.xuat_trong_ky),
                },
                {
                  key: "ton_cuoi_ky",
                  label: "Tồn cuối kỳ",
                  numeric: true,
                  render: (row) => number(row.ton_cuoi_ky),
                },
              ]}
            />
          </QueryState>
        ) : (
          <p>Chọn kỳ và bấm “Xem báo cáo” để tải số liệu.</p>
        )}
      </Card>
    </>
  );
}
