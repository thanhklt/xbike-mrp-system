import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCollection, useDetail } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { nullable } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Field } from "../../components/Field.jsx";
import { Button } from "../../components/Button.jsx";
import { ErrorNotice } from "../../components/QueryState.jsx";
const base = "/kho/nha-cung-cap";
export function SuppliersPage() {
  const { id } = useParams();
  const collection = useCollection(API.suppliers, { sort: "id" });
  const detail = useDetail(API.suppliers, id);
  return (
    <>
      <PageHeader
        title="Nhà cung cấp"
        subtitle="Danh mục dùng khi lập phiếu nhập kho."
        action={
          <Link className="btn btn-primary" to={`${base}/moi`}>
            Thêm nhà cung cấp
          </Link>
        }
      />
      <div>
        <Collection
          collection={collection}
          filters={[
            { name: "tinh", label: "Tỉnh / thành" },
            { name: "phuong", label: "Phường / xã" },
          ]}
          columns={[
            {
              key: "ma_ncc",
              label: "Mã NCC",
              render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_ncc}</Link>,
            },
            { key: "ten_ncc", label: "Tên nhà cung cấp" },
            { key: "so_dien_thoai", label: "Số điện thoại" },
            {
              key: "dia_chi",
              label: "Địa chỉ",
              render: (row) => (
                <>
                  {row.dia_chi}
                  <small>{[row.phuong, row.tinh].filter(Boolean).join(" · ")}</small>
                </>
              ),
            },
            {
              key: "action",
              label: "Thao tác",
              render: (row) => <Link to={`${base}/${row.id}`}>Xem →</Link>,
            },
          ]}
        />
        <RecordPanel
          id={id}
          query={detail}
          base={base}
          title={id === "moi" ? "Thêm nhà cung cấp" : "Chi tiết nhà cung cấp"}
        >
          {(snapshot) =>
            snapshot ? (
              <div className="stack">
                <InfoGrid
                  entries={[
                    ["Mã NCC", snapshot.data.ma_ncc],
                    ["Tên", snapshot.data.ten_ncc],
                    ["Số điện thoại", snapshot.data.so_dien_thoai],
                    ["Địa chỉ", snapshot.data.dia_chi],
                    ["Phường / xã", snapshot.data.phuong],
                    ["Tỉnh / thành", snapshot.data.tinh],
                  ]}
                />
                <div className="actions">
                  <Button variant="secondary" reason="API hiện chỉ hỗ trợ xem và tạo nhà cung cấp.">
                    Sửa
                  </Button>
                  <Button variant="secondary" reason="Chưa có API xóa nhà cung cấp.">
                    Xóa…
                  </Button>
                </div>
                <Link to={`/kho/phieu-nhap?ncc_id=${snapshot.data.id}`}>
                  Xem phiếu nhập của nhà cung cấp →
                </Link>
              </div>
            ) : (
              <SupplierForm />
            )
          }
        </RecordPanel>
      </div>
    </>
  );
}
function SupplierForm() {
  const navigate = useNavigate();
  const { save, busy, error } = useSave();
  const [values, setValues] = useState({
    ma_ncc: "",
    ten_ncc: "",
    so_dien_thoai: "",
    dia_chi: "",
    phuong: "",
    tinh: "",
  });
  function submit(event) {
    event.preventDefault();
    const body = Object.fromEntries(
      Object.entries(values).map(([key, value]) => [key, nullable(value)]),
    );
    save({ path: API.suppliers, body, versioned: false }, (result) =>
      navigate(`${base}/${result.data.id}`),
    );
  }
  return (
    <form className="stack" onSubmit={submit}>
      <ErrorNotice error={error} />
      <div className="form-grid">
        {[
          ["ma_ncc", "Mã NCC", true],
          ["ten_ncc", "Tên nhà cung cấp", true],
          ["so_dien_thoai", "Số điện thoại"],
          ["dia_chi", "Địa chỉ"],
          ["phuong", "Phường / xã"],
          ["tinh", "Tỉnh / thành"],
        ].map(([name, label, required]) => (
          <Field
            key={name}
            label={label}
            required={required}
            pattern={name === "ma_ncc" ? "NCC-[0-9]{6}" : undefined}
            placeholder={name === "ma_ncc" ? "NCC-000001" : undefined}
            value={values[name]}
            onChange={(event) => setValues({ ...values, [name]: event.target.value })}
          />
        ))}
      </div>
      <Button type="submit" disabled={busy}>
        Tạo nhà cung cấp
      </Button>
    </form>
  );
}
