import { Link } from "react-router-dom";
import { Card } from "../../components/Card.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Notice, QueryState } from "../../components/QueryState.jsx";
import { InfoGrid } from "../../components/RecordPanel.jsx";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useChoices, useResource } from "../../lib/api/useResources.js";
import {
  SHORTAGE_COLUMNS,
  shortageRequestEntries,
  shortageRows,
} from "./shortageView.js";

// UC-27 Xem nhu cầu bổ sung linh kiện — Main 1–4, A1 hiển thị yêu cầu chờ và mở form nhập bổ sung (specs/use_cases/production/UC-27.md)
export function ShortagePage() {
  const query = useResource(API.shortages);
  const catalog = useCatalog();
  const employees = useChoices(API.employees);
  const items = catalog.data?.data || [];
  const { yeu_cau: requests = [] } = query.data?.data || {};
  return (
    <>
      <PageHeader
        title="Nhu cầu bổ sung linh kiện"
        subtitle="Xem linh kiện còn thiếu của từng yêu cầu sản xuất đang chờ và lập phiếu nhập bổ sung."
      />
      <Card title="Yêu cầu chờ bổ sung">
        <QueryState query={query}>
          <QueryState query={catalog}>
            <QueryState query={employees}>
              <div className="stack">
                {requests.length ? (
                  requests.map((record) => (
                    <section key={record.id} className="stack">
                      <h3>
                        <Link to={`/kho/yeu-cau/${record.id}`}>{record.ma_yeu_cau_san_xuat}</Link>
                      </h3>
                      <InfoGrid
                        entries={shortageRequestEntries(record, items, employees.data || [])}
                      />
                      {record.da_du ? (
                        <Notice>Đã đủ linh kiện, chờ nhân viên kiểm tra lại.</Notice>
                      ) : (
                        <>
                          <DataTable
                            rows={shortageRows(record.linh_kien_thieu)}
                            columns={SHORTAGE_COLUMNS}
                          />
                          <div className="actions actions-end">
                            <Link
                              className="btn btn-secondary"
                              to={`/kho/phieu-nhap/moi?yeu_cau_san_xuat_id=${record.id}`}
                            >
                              Lập phiếu nhập bổ sung
                            </Link>
                          </div>
                        </>
                      )}
                    </section>
                  ))
                ) : (
                  <Notice>Không có yêu cầu chờ bổ sung linh kiện.</Notice>
                )}
              </div>
            </QueryState>
          </QueryState>
        </QueryState>
      </Card>
    </>
  );
}
