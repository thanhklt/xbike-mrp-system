// In-memory API for browser verification only. This file is not imported by the app.
// Fixed "today" for traffic: 09/11/2026 in Asia/Ho_Chi_Minh, current hour 15h.
const TRAFFIC_TODAY_START = Date.UTC(2026, 10, 8, 17);
const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const TRAFFIC_HOURS = [
  420, 380, 350, 400, 520, 610, 900, 1500, 2100, 2650, 2400, 2300, 2280, 3000, 3550, 3400,
];
const TRAFFIC_DAYS = [
  31000, 29500, 30500, 32000, 28000, 26500, 33000, 34500, 30000, 29000, 31500, 32500, 35000, 27000,
  25500, 33500, 36000, 34000, 30500, 31000, 32000, 29500, 28500, 33000, 35500, 34500, 31000, 30000,
  32500, 33000, 31500, 30500, 34000, 35000, 36500, 12500,
];

export function trafficSeries(range) {
  const iso = (time) => new Date(time).toISOString().replace(".000Z", "Z");
  const end = TRAFFIC_TODAY_START + DAY;
  let points;
  if (range === "hom_nay") {
    points = Array.from({ length: 24 }, (_, hour) => ({
      bat_dau: iso(TRAFFIC_TODAY_START + hour * HOUR),
      so_request: TRAFFIC_HOURS[hour] ?? null,
      trung_binh_7_ngay: null,
    }));
  } else {
    const count = range === "7_ngay" ? 7 : 30;
    const offset = TRAFFIC_DAYS.length - count;
    points = Array.from({ length: count }, (_, index) => {
      const window = TRAFFIC_DAYS.slice(offset + index - 6, offset + index + 1);
      return {
        bat_dau: iso(TRAFFIC_TODAY_START - (count - 1 - index) * DAY),
        so_request: TRAFFIC_DAYS[offset + index],
        trung_binh_7_ngay:
          range === "30_ngay"
            ? Math.round((window.reduce((sum, value) => sum + value, 0) / 7) * 10) / 10
            : null,
      };
    });
  }
  return {
    data: {
      khoang_thoi_gian: range,
      buoc: range === "hom_nay" ? "gio" : "ngay",
      timezone: "Asia/Ho_Chi_Minh",
      tu_thoi_diem: points[0].bat_dau,
      den_thoi_diem_exclusive: iso(end),
      tong_request: points.reduce((sum, point) => sum + (point.so_request ?? 0), 0),
      diem: points,
    },
    meta: { request_id: "traffic-fixture" },
  };
}

export function adminActivityEntries() {
  return [
    {
      loai_doi_tuong: "vai_tro",
      thao_tac: "tao",
      doi_tuong_id: 2,
      du_lieu_sau: { ten_vai_tro: "Quản lý kho" },
    },
    {
      loai_doi_tuong: "nhan_vien",
      thao_tac: "cap_quyen",
      doi_tuong_id: 5,
      du_lieu_truoc: { ma_vai_tro: "nhan_vien" },
      du_lieu_sau: { ma_nhan_vien: "nv005", ho_ten: "Tên lịch sử", ma_vai_tro: "quan_ly" },
    },
    {
      loai_doi_tuong: "nhan_vien",
      thao_tac: "sua",
      doi_tuong_id: 3,
      du_lieu_truoc: { email: "old", so_dien_thoai: "old" },
      du_lieu_sau: {
        ma_nhan_vien: "nv003",
        ho_ten: "Tên lịch sử",
        email: "private@example.test",
        so_dien_thoai: "0909999999",
      },
    },
    { loai_doi_tuong: "nhan_vien", thao_tac: "dang_nhap", nhan_vien_id: 3, doi_tuong_id: 3 },
    {
      loai_doi_tuong: "nhan_vien",
      thao_tac: "vo_hieu_hoa",
      doi_tuong_id: 7,
      du_lieu_sau: { ma_nhan_vien: "nv007", ho_ten: "Tên lịch sử" },
      ly_do: "không còn sử dụng",
    },
    {
      loai_doi_tuong: "nhan_vien",
      thao_tac: "thu_hoi_quyen",
      doi_tuong_id: 5,
      du_lieu_truoc: { ma_vai_tro: "nhan_vien" },
    },
  ].map((entry, index) => ({
    id: index + 1,
    nhan_vien_id: 2,
    created_at: `2026-11-10T0${8 - index}:00:00Z`,
    du_lieu_truoc: null,
    du_lieu_sau: null,
    ly_do: null,
    ...entry,
  }));
}

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
      loai_mat_hang: "linh_kien",
      don_vi_tinh: "cai",
      mau_sac: "den",
      mo_ta: "Khung xe thép",
      don_gia: 250000,
      is_active: true,
      so_luong_ton: 120,
      so_luong_dang_giu: 40,
      so_luong_con_dung: 80,
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
      so_luong_dang_giu: 5,
      so_luong_con_dung: 50,
      ton_kho_updated_at: null,
    },
    {
      id: 3,
      ma_mat_hang: "MH-000003",
      ten_mat_hang: "Cụm bánh xe",
      sku: "WHEEL-01",
      loai_mat_hang: "linh_kien",
      don_vi_tinh: "bo",
      mau_sac: null,
      mo_ta: null,
      don_gia: 300000,
      is_active: true,
      so_luong_ton: 12,
      so_luong_dang_giu: 2,
      so_luong_con_dung: 10,
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
      so_luong_dang_giu: 0,
      so_luong_con_dung: 18,
      ton_kho_updated_at: null,
    },
  ];
  const now = "2026-11-05T01:00:00Z";
  for (const item of items) {
    item.so_luong_dang_giu = item.id === 4 ? 6 : 0;
    item.so_luong_con_dung = item.so_luong_ton - item.so_luong_dang_giu;
  }
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
    loai_yeu_cau: "xuat_giao",
    han_hoan_thanh: "2026-12-01",
    bom_id: null,
    so_luong_dung_thanh_pham: null,
    so_luong_can_san_xuat: null,
    updated_at: now,
    gui_at: null,
    kiem_tra_lan_dau_at: null,
    started_at: null,
    huy_at: null,
    nguoi_huy_id: null,
    ly_do_huy: null,
    phien_ban: 1,
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
    accessToken: "browser-test-token",
    calls: [],
    unexpected: [],
    versions: {},
    resources: {
      nhan_vien: people,
      vai_tro: [
        {
          id: 1,
          ma_vai_tro: "quan_tri_vien",
          ten_vai_tro: "Quản trị viên",
          mo_ta:
            "Quản trị hệ thống và tài khoản người dùng: thêm, vô hiệu hóa và phân quyền tài khoản; không mặc định thực hiện nghiệp vụ kho, sản xuất.",
        },
        {
          id: 2,
          ma_vai_tro: "quan_ly",
          ten_vai_tro: "Quản lý kho",
          mo_ta:
            "Quản lý nguyên vật liệu, thành phẩm, BOM; nhập kho, duyệt xuất kho, duyệt chứng từ hoàn thành sản xuất, yêu cầu sản xuất và báo cáo kho.",
        },
        {
          id: 3,
          ma_vai_tro: "nhan_vien",
          ten_vai_tro: "Nhân viên",
          mo_ta:
            "Lập đề nghị xuất nguyên vật liệu và thành phẩm, kiểm tra vật tư, ghi nhận sản xuất, lập và gửi chứng từ hoàn thành sản xuất.",
        },
      ],
      mat_hang: items,
      chung_tu_hoan_thanh_sx: [],
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
          created_at: now,
          kich_hoat_gan_nhat_at: now,
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
          loai_phieu: "xuat_linh_kien",
          yeu_cau_san_xuat_id: 2,
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
          yeu_cau_san_xuat_id: 2,
          tong_tien: null,
          trang_thai: "nhap",
          created_at: now,
          chi_tiet: [{ id: 2, mat_hang_id: 4, so_luong: 2, don_gia_thuc: null, tong_gia: null }],
        },
      ],
      yeu_cau_san_xuat: [
        request,
        {
          ...request, id: 2, ma_yeu_cau_san_xuat: "YCSX-202611-000002", trang_thai: "dang_thuc_hien",
          bom_id: 1, so_luong_dung_thanh_pham: 12, so_luong_can_san_xuat: 8,
          gui_at: now, kiem_tra_lan_dau_at: now,
        },
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
          access_token: state.accessToken,
          token_type: "bearer",
          expires_in: 3600,
          nhan_vien: user,
        },
        meta: {},
      });
    if (state.accessToken !== "browser-test-token" && call.headers.authorization !== `Bearer ${state.accessToken}`)
      return respond({ error: { message: "Please sign in again" } }, 401);
    if (path === "auth/me") return respond({ data: user, meta: {} }, 200, { etag: '"user-v1"' });
    if (path === "danh_muc_mat_hang")
      return respond({ data: items, meta: { total: items.length } });
    if (path === "luu_luong_truy_cap")
      return respond(trafficSeries(call.params.khoang_thoi_gian || "hom_nay"));
    if (method === "GET" && path === "bao_cao/nhap_xuat_ton") {
      const { ky, nam, thang, quy } = call.params;
      const year = Number(nam);
      const month = ky === "thang" ? Number(thang) : ky === "quy" ? Number(quy) * 3 - 2 : 1;
      const duration = ky === "thang" ? 1 : ky === "quy" ? 3 : 12;
      return respond({
        success: true,
        data: {
          ky,
          nam: year,
          thang: thang ? Number(thang) : null,
          quy: quy ? Number(quy) : null,
          tu_thoi_diem: new Date(Date.UTC(year, month - 1, 1, -7)).toISOString(),
          den_thoi_diem: new Date(Date.UTC(year, month - 1 + duration, 1, -7)).toISOString(),
          mat_hang: [],
        },
        message: "Lấy báo cáo nhập-xuất-tồn thành công",
      });
    }
    if (method === "GET" && path === "bao_cao/bien_dong_kho")
      return respond({
        success: true,
        data: [],
        pagination: {
          page: Number(call.params.page || 1),
          page_size: Number(call.params.page_size || 20),
          total_items: 0,
          total_pages: 0,
          has_next: false,
          has_prev: false,
        },
        message: "Items retrieved successfully",
      });
    if (path === "nhu_cau_bo_sung_linh_kien")
      return respond({ data: { yeu_cau: [], tong_hop: [] }, meta: {} });
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
    if (method === "GET" && rawId)
      return record
        ? respond({ data: record, meta: {} }, 200, { etag: version() })
        : respond({ error: { message: "Không tìm thấy" } }, 404);
    if (method === "GET") {
      let matching = records.filter((entry) =>
        !(resource === "yeu_cau_san_xuat" && role === "nhan_vien" &&
          (entry.trang_thai === "nhap" || entry.nhan_vien_duoc_giao_id !== user.id)) &&
        Object.entries(call.params).every(([key, value]) =>
          key === "bo_thao_tac"
            ? entry.thao_tac !== value
            : ["page", "page_size", "sort", "sort_by", "sort_order"].includes(key) ||
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
      if (resource === "nha_cung_cap") created.ma_ncc = `NCC-${String(nextId).padStart(6, "0")}`;
      if (resource === "mat_hang") {
        Object.assign(created, { ma_mat_hang: `MH-${String(nextId).padStart(6, "0")}`, so_luong_ton: 0, so_luong_dang_giu: 0, so_luong_con_dung: 0, is_active: true });
        if (body.bom) {
          state.resources.bom.push({ id: Math.max(...state.resources.bom.map((entry) => entry.id), 0) + 1, mat_hang_id: nextId, version: 1, created_at: now, kich_hoat_gan_nhat_at: now, is_active: true, da_duoc_su_dung: false, chi_tiet: body.bom.chi_tiet });
        }
      }
      for (const key of ["ma_phieu_nhap", "ma_phieu_xuat", "ma_yeu_cau_san_xuat", "ma_phieu"])
        if (created[key]) created[key] = `${created[key]}-NEW`;
      records.push(created);
      return respond({ data: created, meta: {} }, 201, { etag: '"v1"' });
    }
    if (!record) return respond({ error: { message: "Không tìm thấy" } }, 404);
    if (incoming.headers()["if-match"] !== version())
      return respond(
        { error: { code: "du_lieu_da_thay_doi", message: "Dữ liệu đã thay đổi" }, meta: {} },
        412,
      );
    if (resource === "bom" && action === "phien_ban" && method === "POST") {
      const next = { ...record, ...body, id: Math.max(...records.map((entry) => entry.id)) + 1, version: Math.max(...records.filter((entry) => entry.mat_hang_id === record.mat_hang_id).map((entry) => entry.version)) + 1, is_active: true, created_at: now, kich_hoat_gan_nhat_at: now, da_duoc_su_dung: false };
      for (const entry of records.filter((entry) => entry.mat_hang_id === record.mat_hang_id)) entry.is_active = false;
      state.versions[`${resource}/${id}`] = (state.versions[`${resource}/${id}`] || 1) + 1;
      records.push(next);
      return respond({ data: next, meta: {} }, 201, { etag: '"v1"' });
    if (resource === "nhan_vien" && method === "PATCH" && body.ten_dang_nhap !== undefined) {
      body.ten_dang_nhap = body.ten_dang_nhap.trim();
      if (records.some((entry) => entry.id !== id && entry.ten_dang_nhap === body.ten_dang_nhap))
        return respond(
          { error: { code: "ten_dang_nhap_bi_trung", message: "Tên đăng nhập đã tồn tại" }, meta: {} },
          409,
        );
    }
    if (resource === "nhan_vien" && action === "dat_lai_mat_khau" && method === "POST") {
      if (id === user.id) state.accessToken = "browser-test-token-renewed";
      return respond({ data: record, meta: {} }, 200, { etag: version() });
    }
    if (resource === "yeu_cau_san_xuat" && action === "bat_dau") {
      if (role !== "nhan_vien" || record.nhan_vien_duoc_giao_id !== user.id)
        return respond({ error: { message: "Không có quyền" }, meta: {} }, 403);
      if (record.started_at)
        return respond({ data: record, meta: {} }, 200, { etag: version() });
      if (record.trang_thai !== "dang_thuc_hien" || record.so_luong_can_san_xuat <= 0)
        return respond({ error: { message: "Trạng thái không hợp lệ" }, meta: {} }, 409);
      if (!state.resources.phieu_xuat.some((issue) =>
        issue.yeu_cau_san_xuat_id === id && issue.loai_phieu === "xuat_linh_kien" && issue.trang_thai === "da_duyet"))
        return respond({ error: { message: "Phiếu xuất linh kiện chưa được duyệt" }, meta: {} }, 409);
    }
    state.versions[`${resource}/${id}`] = (state.versions[`${resource}/${id}`] || 1) + 1;
    if (resource === "yeu_cau_san_xuat" && action === "bat_dau") {
      record.started_at = now;
      record.phien_ban += 1;
      record.updated_at = now;
    }
    if (method === "PATCH" || method === "PUT") {
      Object.assign(record, body);
      if (resource === "nhan_vien" && action === "vai_tro" && body.vai_tro_id !== undefined) {
        const matchedRole = state.resources.vai_tro.find(
          (entry) => entry.id === Number(body.vai_tro_id),
        );
        if (matchedRole) record.ma_vai_tro = matchedRole.ma_vai_tro;
      }
    }
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
        action === "gui" && resource === "yeu_cau_san_xuat"
          ? "da_gui"
          : transitions[action];
    if (action === "nhan_xu_ly") record.nguoi_xu_ly_id = user.id;
    if (action === "giai_quyet") Object.assign(record, body);
    if (resource === "bom") record.is_active = method !== "DELETE";
    return respond({ data: record, meta: {} }, 200, { etag: version() });
  });
  return state;
}
