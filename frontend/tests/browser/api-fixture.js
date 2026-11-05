// In-memory API for browser verification only. This file is not imported by the app.
export async function installApi(page, { role = "quan_ly", authenticated = true, intercept } = {}) {
  const people = [
    {
      id: 1,
      ten_dang_nhap: "admin",
      ma_nhan_vien: "NV-000001",
      ho_ten: "Lê Văn Thành",
      ma_vai_tro: "quan_tri_vien",
      vai_tro_id: 1,
      trang_thai: "hoat_dong",
      email: "admin@example.test",
      so_dien_thoai: null,
      ngay_sinh: null,
      ngay_vao_lam: null,
      he_so_luong: null,
    },
    {
      id: 2,
      ten_dang_nhap: "manager",
      ma_nhan_vien: "NV-000002",
      ho_ten: "Nguyễn Văn An",
      ma_vai_tro: "quan_ly",
      vai_tro_id: 2,
      trang_thai: "hoat_dong",
      email: "manager@example.test",
      so_dien_thoai: "0900000000",
      ngay_sinh: null,
      ngay_vao_lam: "2026-01-01",
      he_so_luong: "1.50",
    },
    {
      id: 3,
      ten_dang_nhap: "employee",
      ma_nhan_vien: "NV-000003",
      ho_ten: "Đặng Quốc Bình",
      ma_vai_tro: "nhan_vien",
      vai_tro_id: 3,
      trang_thai: "hoat_dong",
      email: "employee@example.test",
      so_dien_thoai: null,
      ngay_sinh: null,
      ngay_vao_lam: null,
      he_so_luong: null,
    },
  ];
  const items = [
    {
      id: 1,
      ma_mat_hang: "MH-000001",
      ten_mat_hang: "Khung xe",
      sku: "FRAME-01",
      loai_mat_hang: "nguyen_vat_lieu",
      don_vi_tinh: "cai",
      mau_sac: "den",
      mo_ta: "Khung xe thép",
      don_gia: 250000,
      is_active: true,
      so_luong_ton: 120,
      ton_kho_updated_at: "2026-11-05T01:00:00Z",
    },
    {
      id: 2,
      ma_mat_hang: "MH-000002",
      ten_mat_hang: "Yên xe",
      sku: "SEAT-01",
      loai_mat_hang: "linh_kien",
      don_vi_tinh: "cai",
      mau_sac: null,
      mo_ta: null,
      don_gia: 80000,
      is_active: true,
      so_luong_ton: 55,
      ton_kho_updated_at: null,
    },
    {
      id: 3,
      ma_mat_hang: "MH-000003",
      ten_mat_hang: "Cụm bánh xe",
      sku: "WHEEL-01",
      loai_mat_hang: "ban_thanh_pham",
      don_vi_tinh: "bo",
      mau_sac: null,
      mo_ta: null,
      don_gia: 300000,
      is_active: true,
      so_luong_ton: 12,
      ton_kho_updated_at: null,
    },
    {
      id: 4,
      ma_mat_hang: "MH-000004",
      ten_mat_hang: "Xe đạp City Ride",
      sku: "CITY-01",
      loai_mat_hang: "thanh_pham",
      don_vi_tinh: "chiếc",
      mau_sac: "trang",
      mo_ta: null,
      don_gia: 2500000,
      is_active: true,
      so_luong_ton: 18,
      ton_kho_updated_at: null,
    },
  ];
  const now = "2026-11-05T01:00:00Z";
  const lines = [{ id: 1, mat_hang_id: 1, so_luong: 10, don_gia_thuc: 250000, tong_gia: 2500000 }];
  const request = {
    id: 1,
    ma_yeu_cau_san_xuat: "YCSX-202611-000001",
    mat_hang_id: 4,
    so_luong: 20,
    nhan_vien_id: 2,
    nhan_vien_duoc_giao_id: 3,
    trang_thai: "nhap",
    created_at: now,
    completed_at: null,
    so_luong_da_xuat: 0,
    so_luong_con_phai_xuat: 20,
    lenh_san_xuat_ids: [1],
  };
  const order = {
    id: 1,
    ma_lenh_san_xuat: "LSX-202611-000001",
    yeu_cau_san_xuat_id: 1,
    lenh_san_xuat_cha_id: null,
    mat_hang_id: 4,
    bom_id: 1,
    so_luong: 8,
    nhan_vien_id: 3,
    trang_thai: "da_gui",
    created_at: now,
    started_at: null,
    completed_at: null,
    nhu_cau_truc_tiep: [{ id: 1, mat_hang_id: 1, so_luong_can: 8 }],
    so_luong_da_hoan_thanh: 0,
    so_luong_con_phai_hoan_thanh: 8,
    lenh_con_ids: [],
  };
  const completion = {
    id: 1,
    ma_phieu: "HTSX-202611-000001",
    lenh_san_xuat_id: 1,
    mat_hang_id: 4,
    so_luong_hoan_thanh: 2,
    nhan_vien_id: 3,
    trang_thai: "nhap",
    finish_time: now,
    created_at: now,
  };
  const receipt = {
    id: 1,
    ma_phieu_nhap: "PN-202611-000001",
    nhan_vien_id: 2,
    ncc_id: 1,
    ngay_nhap: "2026-11-05",
    ghi_chu: "Nhập vật tư",
    tong_tien: 2500000,
    trang_thai: "nhap",
    created_at: now,
    chi_tiet: lines,
  };
  const state = {
    role,
    calls: [],
    unexpected: [],
    versions: {},
    resources: {
      nhan_vien: people,
      vai_tro: [
        { id: 1, ma_vai_tro: "quan_tri_vien", ten_vai_tro: "Quản trị viên" },
        { id: 2, ma_vai_tro: "quan_ly", ten_vai_tro: "Quản lý kho" },
        { id: 3, ma_vai_tro: "nhan_vien", ten_vai_tro: "Nhân viên" },
      ],
      mat_hang: items,
      nha_cung_cap: [
        {
          id: 1,
          ma_ncc: "NCC-000001",
          ten_ncc: "Công ty linh kiện Minh Phát",
          so_dien_thoai: "0901234567",
          dia_chi: "12 Nguyễn Văn Linh",
          phuong: "Tân Phong",
          tinh: "TP. Hồ Chí Minh",
        },
      ],
      bom: [
        {
          id: 1,
          mat_hang_id: 4,
          version: 1,
          start_time: now,
          end_time: null,
          is_active: true,
          da_duoc_su_dung: true,
          chi_tiet: [
            { id: 1, mat_hang_id: 1, so_luong: 1 },
            { id: 2, mat_hang_id: 3, so_luong: 2 },
          ],
        },
      ],
      phieu_nhap: [
        receipt,
        { ...receipt, id: 2, ma_phieu_nhap: "PN-202611-000002", trang_thai: "hoan_thanh" },
      ],
      phieu_xuat: [
        {
          id: 1,
          ma_phieu_xuat: "PX-202611-000001",
          nhan_vien_id: 2,
          loai_phieu: "xuat_vat_tu",
          lenh_san_xuat_id: 1,
          yeu_cau_san_xuat_id: null,
          tong_tien: null,
          trang_thai: "cho_duyet",
          created_at: now,
          chi_tiet: lines,
        },
        {
          id: 2,
          ma_phieu_xuat: "PX-202611-000002",
          nhan_vien_id: 2,
          loai_phieu: "xuat_thanh_pham",
          lenh_san_xuat_id: null,
          yeu_cau_san_xuat_id: 2,
          tong_tien: null,
          trang_thai: "nhap",
          created_at: now,
          chi_tiet: [{ id: 2, mat_hang_id: 4, so_luong: 2, don_gia_thuc: null, tong_gia: null }],
        },
      ],
      yeu_cau_san_xuat: [
        request,
        { ...request, id: 2, ma_yeu_cau_san_xuat: "YCSX-202611-000002", trang_thai: "da_gui" },
      ],
      lenh_san_xuat: [
        order,
        {
          ...order,
          id: 2,
          ma_lenh_san_xuat: "LSX-202611-000002",
          trang_thai: "dang_thuc_hien",
          started_at: now,
        },
      ],
      chung_tu_hoan_thanh_sx: [
        completion,
        { ...completion, id: 2, ma_phieu: "HTSX-202611-000002", trang_thai: "cho_duyet" },
      ],
      phieu_dieu_chinh_kho: [
        {
          id: 1,
          ma_phieu: "DCK-202611-000001",
          phieu_nhap_id: 2,
          nhan_vien_id: 2,
          ly_do: "Điều chỉnh số lượng thực nhận",
          trang_thai: "nhap",
          created_at: now,
          confirmed_at: null,
          chi_tiet: [
            {
              id: 1,
              mat_hang_id: 1,
              giao_dich_goc_id: 101,
              so_luong_hieu_luc_truoc: 10,
              so_luong_dung: 8,
              so_luong_bien_dong: -2,
            },
          ],
        },
      ],
      ticket_loi_dieu_chinh: [
        {
          id: 1,
          ma_ticket: "TKDC-202611-000001",
          phieu_nhap_id: 2,
          nguoi_tao_id: 2,
          mo_ta_loi: "Không đủ tồn để điều chỉnh",
          trang_thai: "cho_xu_ly",
          nguoi_xu_ly_id: null,
          ket_qua_xu_ly: null,
          created_at: now,
          closed_at: null,
          chi_tiet: [
            {
              id: 1,
              chi_tiet_phieu_nhap_id: 1,
              mat_hang_id: 1,
              so_luong_hieu_luc_truoc: 10,
              so_luong_de_nghi: 8,
              so_luong_bien_dong: -2,
              ton_kho_tai_thoi_diem: 1,
            },
          ],
        },
      ],
      audit: [
        {
          id: 1,
          nhan_vien_id: 2,
          loai_doi_tuong: "phieu_nhap",
          doi_tuong_id: 2,
          thao_tac: "hoan_tat",
          ly_do: null,
          created_at: now,
          du_lieu_truoc: { trang_thai: "nhap" },
          du_lieu_sau: { trang_thai: "hoan_thanh", protected_marker: "MANAGER_ONLY" },
        },
      ],
    },
  };
  if (authenticated)
    await page.addInitScript(() =>
      localStorage.setItem("xbike_access_token", "browser-test-token"),
    );
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
  await page.route("**/api/v1/**", async (route) => {
    const incoming = route.request();
    const url = new URL(incoming.url());
    const path = url.pathname.replace("/api/v1/", "").replace(/\/$/, "");
    const method = incoming.method();
    const body = incoming.postData() ? incoming.postDataJSON() : {};
    const call = {
      path,
      method,
      body,
      headers: incoming.headers(),
      params: Object.fromEntries(url.searchParams),
    };
    state.calls.push(call);
    async function respond(payload, status = 200, headers = {}) {
      await route.fulfill({
        status,
        contentType: "application/json",
        headers,
        body: status === 204 ? undefined : JSON.stringify(payload),
      });
    }
    const override = await intercept?.(call, state);
    if (override) return respond(override.json, override.status || 200, override.headers);
    const user = people.find((person) => person.ma_vai_tro === state.role);
    if (path === "auth/dang_nhap")
      return respond({
        data: {
          access_token: "browser-test-token",
          token_type: "bearer",
          expires_in: 3600,
          nhan_vien: user,
        },
        meta: {},
      });
    if (path === "auth/me") return respond({ data: user, meta: {} }, 200, { etag: '"user-v1"' });
    if (path === "auth/doi_mat_khau") return respond({ data: { da_doi: true }, meta: {} });
    if (path === "danh_muc_mat_hang")
      return respond({ data: items, meta: { total: items.length } });
    const [resource, rawId, action] = path.split("/");
    const records = state.resources[resource];
    if (!records) {
      state.unexpected.push(call);
      return respond({ error: { message: "Unsupported fixture endpoint" } }, 501);
    }
    const id = Number(rawId);
    const record = records.find((entry) => entry.id === id);
    const version = () => `"v${state.versions[`${resource}/${id}`] || 1}"`;
    if (action === "cau_truc")
      return respond({
        data: {
          bom_id: id,
          mat_hang_id: 4,
          version: 1,
          children: [
            { mat_hang_id: 1, so_luong_tren_mot_don_vi_cha: 1, bom_id: null, children: [] },
            {
              mat_hang_id: 3,
              so_luong_tren_mot_don_vi_cha: 2,
              bom_id: 2,
              children: [
                { mat_hang_id: 2, so_luong_tren_mot_don_vi_cha: 1, bom_id: null, children: [] },
              ],
            },
          ],
        },
        meta: {},
      });
    if (action === "vat_tu")
      return respond(
        {
          data: {
            lenh_san_xuat_id: id,
            du_dieu_kien_bat_dau: true,
            chi_tiet: [
              {
                mat_hang_id: 1,
                so_luong_can: 8,
                so_luong_da_cap: 8,
                so_luong_con_phai_cap: 0,
                ton_hien_tai: 120,
              },
            ],
          },
          meta: {},
        },
        200,
        { etag: version() },
      );
    if (action === "ke_hoach")
      return respond({ data: { yeu_cau_san_xuat_id: id, lenh: [order] }, meta: {} });
    if (action === "tinh_ke_hoach")
      return respond({
        data: {
          yeu_cau_san_xuat_id: id,
          tinh_luc: now,
          ke_hoach_token: "plan-test-token",
          so_luong_yeu_cau: 20,
          ton_thanh_pham: 18,
          so_luong_can_san_xuat: 2,
          du_dieu_kien_gui: true,
          thieu_vat_tu: false,
          lenh_du_kien: [
            { ma_tam: "L1", ma_cha_tam: null, mat_hang_id: 4, bom_id: 1, so_luong: 2 },
          ],
          vat_tu: [
            {
              mat_hang_id: 1,
              ma_mat_hang: "MH-000001",
              ten_mat_hang: "Khung xe",
              don_vi_tinh: "cai",
              so_luong_can_tu_kho: 2,
              so_luong_hien_co: 120,
              so_luong_thieu: 0,
            },
          ],
        },
        meta: {},
      });
    if (method === "GET" && rawId)
      return record
        ? respond({ data: record, meta: {} }, 200, { etag: version() })
        : respond({ error: { message: "Không tìm thấy" } }, 404);
    if (method === "GET") {
      let matching = records.filter((entry) =>
        Object.entries(call.params).every(([key, value]) =>
          ["page", "page_size", "sort", "sort_by", "sort_order"].includes(key) ||
          ["q", "search"].includes(key)
            ? !["q", "search"].includes(key) ||
              JSON.stringify(entry).toLowerCase().includes(value.toLowerCase())
            : String(entry[key]) === value,
        ),
      );
      const pageNumber = Number(url.searchParams.get("page") || 1),
        pageSize = Number(url.searchParams.get("page_size") || 20);
      const total = matching.length;
      matching = matching.slice((pageNumber - 1) * pageSize, pageNumber * pageSize);
      if (resource === "audit")
        return respond({
          data: matching,
          success: true,
          pagination: {
            page: pageNumber,
            page_size: pageSize,
            total_items: total,
            total_pages: Math.ceil(total / pageSize),
          },
        });
      return respond({
        data: matching,
        meta: {
          page: pageNumber,
          page_size: pageSize,
          total,
          total_pages: Math.ceil(total / pageSize),
        },
      });
    }
    if (!rawId && method === "POST") {
      const nextId = Math.max(...records.map((entry) => entry.id), 0) + 1;
      const created = { ...records[0], ...body, id: nextId, trang_thai: "nhap", created_at: now };
      for (const key of ["ma_phieu_nhap", "ma_phieu_xuat", "ma_yeu_cau_san_xuat", "ma_phieu"])
        if (created[key]) created[key] = `${created[key]}-NEW`;
      records.push(created);
      return respond({ data: created, meta: {} }, 201, { etag: '"v1"' });
    }
    if (!record) return respond({ error: { message: "Không tìm thấy" } }, 404);
    if (resource !== "bom" && incoming.headers()["if-match"] !== version())
      return respond(
        { error: { code: "du_lieu_da_thay_doi", message: "Dữ liệu đã thay đổi" }, meta: {} },
        412,
      );
    state.versions[`${resource}/${id}`] = (state.versions[`${resource}/${id}`] || 1) + 1;
    if (method === "PATCH" || method === "PUT") Object.assign(record, body);
    if (method === "DELETE" && resource === "mat_hang") {
      record.is_active = false;
      return respond(null, 204);
    }
    if (method === "DELETE" && resource !== "nhan_vien" && resource !== "bom") {
      records.splice(records.indexOf(record), 1);
      return respond(null, 204);
    }
    if (method === "DELETE" && resource === "nhan_vien") {
      record.trang_thai = "bi_khoa";
      return respond(null, 204);
    }
    const transitions = {
      gui: "cho_duyet",
      duyet: "da_duyet",
      tu_choi: "tu_choi",
      ve_nhap: "nhap",
      bat_dau: "dang_thuc_hien",
      huy: "da_huy",
      hoan_tat: "hoan_thanh",
      xac_nhan: "da_xac_nhan",
      nhan_xu_ly: "dang_xu_ly",
      giai_quyet: "da_xu_ly",
      mo_khoa: "hoat_dong",
    };
    if (action && transitions[action])
      record.trang_thai =
        action === "gui" && ["lenh_san_xuat", "yeu_cau_san_xuat"].includes(resource)
          ? "da_gui"
          : transitions[action];
    if (action === "nhan_xu_ly") record.nguoi_xu_ly_id = user.id;
    if (action === "giai_quyet") Object.assign(record, body);
    if (resource === "bom") record.is_active = method !== "DELETE";
    const result =
      action === "gui" && resource === "yeu_cau_san_xuat"
        ? { yeu_cau: record, ke_hoach: { lenh: [order] } }
        : record;
    return respond({ data: result, meta: {} }, 200, { etag: version() });
  });
  return state;
}
