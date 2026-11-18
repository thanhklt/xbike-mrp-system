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
          nhan_vien_id: 3,
          loai_phieu: "xuat_linh_kien",
          yeu_cau_san_xuat_id: 2,
          tong_tien: null,
          trang_thai: "cho_duyet",
          created_at: now,
          chi_tiet: [{ id: 1, mat_hang_id: 1, so_luong: 8, don_gia_thuc: null, tong_gia: null }],
        },
        {
          id: 2,
          ma_phieu_xuat: "PX-202611-000002",
          nhan_vien_id: 3,
          loai_phieu: "xuat_thanh_pham",
          yeu_cau_san_xuat_id: 2,
          tong_tien: null,
          trang_thai: "nhap",
          created_at: now,
          chi_tiet: [{ id: 2, mat_hang_id: 4, so_luong: 2, don_gia_thuc: null, tong_gia: null }],
        },
      ],
      chung_tu_hoan_thanh_sx: [],
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
      return respond({ data: { yeu_cau: [] }, meta: {} });
    if (path === "nhan_vien/me/doi_mat_khau" && method === "POST") {
      if (role !== "nhan_vien") {
        return respond({ error: { message: "Không có quyền" } }, 403);
      }
      const { mat_khau_hien_tai, mat_khau_moi } = body;
      if (!mat_khau_hien_tai || !mat_khau_moi || mat_khau_moi.length < 6) {
        return respond({ error: { message: "Dữ liệu không hợp lệ" } }, 422);
      }
      if (mat_khau_hien_tai !== (state.currentPassword || "123456")) {
        return respond({ error: { code: "mat_khau_hien_tai_khong_dung", message: "Mật khẩu hiện tại không chính xác" } }, 400);
      }
      state.currentPassword = mat_khau_moi;
      state.sessionVersion = (state.sessionVersion || 1) + 1;
      return respond(null, 204);
    }
    if (path === "phieu_xuat/cua_toi" && method === "GET") {
      if (role !== "nhan_vien") {
        return respond({ error: { message: "Không có quyền truy cập danh sách" } }, 403);
      }
      const allowedKeys = new Set(["page", "page_size", "loai_phieu", "trang_thai", "yeu_cau_san_xuat_id", "tu_ngay", "den_ngay", "q", "sort"]);
      for (const k of Object.keys(call.params)) {
        if (!allowedKeys.has(k)) {
          return respond({ error: { message: `Tham số không hợp lệ: ${k}` } }, 422);
        }
      }
      if (call.params.den_ngay === "9999-12-31") {
        return respond({ error: { message: "den_ngay ngoài khoảng hỗ trợ" } }, 422);
      }
      if (call.params.tu_ngay && call.params.den_ngay && call.params.tu_ngay > call.params.den_ngay) {
        return respond({ error: { message: "tu_ngay phải nhỏ hơn hoặc bằng den_ngay" } }, 422);
      }
      if (call.params.yeu_cau_san_xuat_id !== undefined) {
        const ycsxId = Number(call.params.yeu_cau_san_xuat_id);
        if (Number.isNaN(ycsxId) || ycsxId <= 0) {
          return respond({ error: { message: "yeu_cau_san_xuat_id phải lớn hơn 0" } }, 422);
        }
        if (ycsxId > 2147483647) {
          return respond({
            data: [],
            meta: { total: 0, page: 1, page_size: Number(call.params.page_size || 20), total_pages: 0, request_id: "req-issue-cua-toi" },
          });
        }
      }

      const myRequests = state.resources.yeu_cau_san_xuat.filter((entry) => entry.nhan_vien_duoc_giao_id === user.id);
      const myRequestIds = new Set(myRequests.map((r) => r.id));
      const requestMap = new Map(myRequests.map((r) => [r.id, r]));

      let matching = state.resources.phieu_xuat.filter((issue) => myRequestIds.has(issue.yeu_cau_san_xuat_id));

      if (call.params.q) {
        const query = call.params.q.toLowerCase();
        matching = matching.filter((issue) => (issue.ma_phieu_xuat || "").toLowerCase().includes(query));
      }
      if (call.params.loai_phieu) {
        matching = matching.filter((issue) => issue.loai_phieu === call.params.loai_phieu);
      }
      if (call.params.trang_thai) {
        matching = matching.filter((issue) => issue.trang_thai === call.params.trang_thai);
      }
      if (call.params.yeu_cau_san_xuat_id) {
        matching = matching.filter((issue) => issue.yeu_cau_san_xuat_id === Number(call.params.yeu_cau_san_xuat_id));
      }
      if (call.params.tu_ngay) {
        matching = matching.filter((issue) => (issue.created_at || "") >= call.params.tu_ngay);
      }
      if (call.params.den_ngay) {
        matching = matching.filter((issue) => (issue.created_at || "").slice(0, 10) <= call.params.den_ngay);
      }

      const sortParam = call.params.sort || "-created_at";
      matching.sort((a, b) => {
        if (sortParam === "id") return a.id - b.id;
        if (sortParam === "-id") return b.id - a.id;
        if (sortParam === "ma_phieu_xuat") return (a.ma_phieu_xuat || "").localeCompare(b.ma_phieu_xuat || "");
        if (sortParam === "-ma_phieu_xuat") return (b.ma_phieu_xuat || "").localeCompare(a.ma_phieu_xuat || "");
        if (sortParam === "created_at") {
          const timeDiff = new Date(a.created_at || 0) - new Date(b.created_at || 0);
          return timeDiff !== 0 ? timeDiff : a.id - b.id;
        }
        const timeDiff = new Date(b.created_at || 0) - new Date(a.created_at || 0);
        return timeDiff !== 0 ? timeDiff : b.id - a.id;
      });

      const pageNumber = Number(call.params.page || 1);
      const pageSize = Number(call.params.page_size || 20);
      const total = matching.length;
      const paged = matching.slice((pageNumber - 1) * pageSize, pageNumber * pageSize).map((issue) => ({
        ...issue,
        ma_yeu_cau_san_xuat: requestMap.get(issue.yeu_cau_san_xuat_id)?.ma_yeu_cau_san_xuat || null,
      }));

      return respond({
        data: paged,
        meta: {
          total,
          page: pageNumber,
          page_size: pageSize,
          total_pages: Math.max(1, Math.ceil(total / pageSize)),
          request_id: "req-issue-cua-toi",
        },
      });
    }
    if (path === "chung_tu_hoan_thanh_sx/cua_toi" && method === "GET") {
      if (role !== "nhan_vien") {
        return respond({ error: { message: "Không có quyền truy cập danh sách" } }, 403);
      }
      const allowedKeys = new Set(["page", "page_size", "mat_hang_id", "trang_thai", "loai_yeu_cau", "tu_ngay", "den_ngay"]);
      for (const k of Object.keys(call.params)) {
        if (!allowedKeys.has(k)) {
          return respond({ error: { message: `Tham số không hợp lệ: ${k}` } }, 422);
        }
      }
      if (call.params.den_ngay === "9999-12-31") {
        return respond({ error: { message: "den_ngay ngoài khoảng hỗ trợ" } }, 422);
      }
      if (call.params.tu_ngay && call.params.den_ngay && call.params.tu_ngay > call.params.den_ngay) {
        return respond({ error: { message: "tu_ngay phải nhỏ hơn hoặc bằng den_ngay" } }, 422);
      }
      if (call.params.mat_hang_id !== undefined) {
        const mhId = Number(call.params.mat_hang_id);
        if (Number.isNaN(mhId) || mhId <= 0) {
          return respond({ error: { message: "mat_hang_id phải lớn hơn 0" } }, 422);
        }
        if (mhId > 2147483647) {
          return respond({
            data: [],
            meta: { total: 0, page: 1, page_size: Number(call.params.page_size || 20), total_pages: 0, request_id: "req-comp-cua-toi" },
          });
        }
      }
      const myRequests = state.resources.yeu_cau_san_xuat.filter((entry) => entry.nhan_vien_duoc_giao_id === user.id);
      const myRequestIds = new Set(myRequests.map((r) => r.id));
      const requestMap = new Map(myRequests.map((r) => [r.id, r]));

      let matching = state.resources.chung_tu_hoan_thanh_sx.filter((comp) => myRequestIds.has(comp.yeu_cau_san_xuat_id));

      if (call.params.trang_thai) {
        matching = matching.filter((comp) => comp.trang_thai === call.params.trang_thai);
      }
      if (call.params.loai_yeu_cau) {
        matching = matching.filter((comp) => requestMap.get(comp.yeu_cau_san_xuat_id)?.loai_yeu_cau === call.params.loai_yeu_cau);
      }
      if (call.params.mat_hang_id) {
        const mhId = Number(call.params.mat_hang_id);
        matching = matching.filter((comp) => comp.mat_hang_id === mhId || requestMap.get(comp.yeu_cau_san_xuat_id)?.mat_hang_id === mhId);
      }
      if (call.params.tu_ngay) {
        matching = matching.filter((comp) => (comp.finish_time || comp.created_at || "") >= call.params.tu_ngay);
      }
      if (call.params.den_ngay) {
        matching = matching.filter((comp) => (comp.finish_time || comp.created_at || "").slice(0, 10) <= call.params.den_ngay);
      }

      matching.sort((a, b) => {
        if (!a.finish_time && !b.finish_time) return b.id - a.id;
        if (!a.finish_time) return 1;
        if (!b.finish_time) return -1;
        const timeDiff = new Date(b.finish_time) - new Date(a.finish_time);
        return timeDiff !== 0 ? timeDiff : b.id - a.id;
      });

      const pageNumber = Number(call.params.page || 1);
      const pageSize = Number(call.params.page_size || 20);
      const total = matching.length;
      const paged = matching.slice((pageNumber - 1) * pageSize, pageNumber * pageSize).map((comp) => {
        const req = requestMap.get(comp.yeu_cau_san_xuat_id);
        return {
          ...comp,
          ma_yeu_cau_san_xuat: req?.ma_yeu_cau_san_xuat || null,
          mat_hang_id: comp.mat_hang_id || req?.mat_hang_id || null,
          loai_yeu_cau: req?.loai_yeu_cau || null,
        };
      });

      return respond({
        data: paged,
        meta: {
          total,
          page: pageNumber,
          page_size: pageSize,
          total_pages: Math.max(1, Math.ceil(total / pageSize)),
          request_id: "req-comp-cua-toi",
        },
      });
    }
    const [resource, rawId, action] = path.split("/");
    if (resource === "phieu_xuat" && method === "GET" && ["theo_yeu_cau", "xem_truoc"].includes(rawId)) {
      const source = state.resources.yeu_cau_san_xuat.find((entry) => entry.id === Number(action));
      if (!["quan_ly", "nhan_vien"].includes(role) || (rawId === "xem_truoc" && role !== "nhan_vien"))
        return respond({ error: { message: "Không có quyền" } }, 403);
      if (!source) return respond({ error: { message: "Không tìm thấy" } }, 404);
      if (role === "nhan_vien" && source.nhan_vien_duoc_giao_id !== user.id)
        return respond({ error: { message: "Không có quyền" } }, 403);
      const saved = state.resources.phieu_xuat.filter((entry) => entry.yeu_cau_san_xuat_id === source.id);
      if (rawId === "theo_yeu_cau") return respond({ data: saved.map(({ id, ma_phieu_xuat, loai_phieu, trang_thai }) =>
        ({ id, ma_phieu_xuat, loai_phieu, trang_thai })), meta: {} });
      const type = call.params.loai_phieu;
      if (!["xuat_linh_kien", "xuat_thanh_pham"].includes(type)) return respond({ error: { message: "Loại phiếu không hợp lệ" } }, 422);
      const completed = state.resources.chung_tu_hoan_thanh_sx.find((entry) => entry.yeu_cau_san_xuat_id === source.id);
      if (source.trang_thai !== "dang_thuc_hien" || saved.some((entry) => entry.loai_phieu === type) ||
        (type === "xuat_linh_kien" ? !(source.so_luong_can_san_xuat > 0) :
          source.loai_yeu_cau !== "xuat_giao" || !(source.so_luong_can_san_xuat === 0 || completed?.trang_thai === "da_duyet")))
        return respond({ error: { message: "Yêu cầu chưa đủ điều kiện hoặc đã có phiếu" } }, 409);
      return respond({ data: { yeu_cau_san_xuat_id: source.id, loai_phieu: type,
        chi_tiet: [{ mat_hang_id: type === "xuat_linh_kien" ? 1 : source.mat_hang_id,
          so_luong: type === "xuat_linh_kien" ? source.so_luong_can_san_xuat : source.so_luong }] }, meta: {} });
    }
    const records = state.resources[resource];
    if (!records) {
      state.unexpected.push(call);
      return respond({ error: { message: "Unsupported fixture endpoint" } }, 501);
    }
    const id = Number(rawId);
    const record = records.find((entry) => entry.id === id);
    const version = () => `"v${state.versions[`${resource}/${id}`] || 1}"`;
    if (resource === "yeu_cau_san_xuat" && action === "chung_tu_hoan_thanh" && method === "GET") {
      if (!record || (role === "nhan_vien" && record.nhan_vien_duoc_giao_id !== user.id))
        return respond({ error: { message: "Không có quyền" } }, 403);
      const document = state.resources.chung_tu_hoan_thanh_sx.find((entry) => entry.yeu_cau_san_xuat_id === id);
      const visible = document && !(role === "quan_ly" && document.trang_thai === "nhap") ? document : null;
      return respond({ data: visible, meta: {} }, 200, visible ? { etag: `"v${state.versions[`chung_tu_hoan_thanh_sx/${document.id}`] || 1}"` } : {});
    }
    if (resource === "chung_tu_hoan_thanh_sx") {
      const source = state.resources.yeu_cau_san_xuat.find((entry) => entry.id === (record?.yeu_cau_san_xuat_id || body.yeu_cau_san_xuat_id));
      if (record && role === "nhan_vien" && source?.nhan_vien_duoc_giao_id !== user.id)
        return respond({ error: { message: "Không có quyền" } }, 403);
      if (["PATCH", "DELETE", "PUT"].includes(method) || action === "ve_nhap")
        return respond({ error: { message: "Không có thao tác này" } }, 405);
      if (!rawId && method === "POST") {
        if (role !== "nhan_vien" || source?.nhan_vien_duoc_giao_id !== user.id)
          return respond({ error: { message: "Không có quyền" } }, 403);
        if (Object.keys(body).join(",") !== "yeu_cau_san_xuat_id")
          return respond({ error: { message: "Payload không đúng hợp đồng" } }, 422);
        if (source.trang_thai !== "dang_thuc_hien" || !source.started_at || !(source.so_luong_can_san_xuat > 0) || records.some((entry) => entry.yeu_cau_san_xuat_id === source.id))
          return respond({ error: { message: "Yêu cầu chưa đủ điều kiện hoặc đã có chứng từ" } }, 409);
        const nextId = Math.max(0, ...records.map((entry) => entry.id)) + 1;
        const created = { id: nextId, ma_phieu: `HTSX-FIXTURE-${nextId}`, ...body, nhan_vien_id: user.id,
          so_luong_hoan_thanh: source.so_luong_can_san_xuat, finish_time: null, trang_thai: "nhap", created_at: now };
        records.push(created);
        return respond({ data: created, meta: {} }, 201, { etag: '"v1"' });
      }
      if (method === "POST" && action === "gui" && (role !== "nhan_vien" || source?.nhan_vien_duoc_giao_id !== user.id))
        return respond({ error: { message: "Không có quyền" } }, 403);
      if (method === "POST" && action === "gui" && (Object.keys(body).length || !["nhap", "tu_choi"].includes(record?.trang_thai)))
        return respond({ error: { message: "Trạng thái hoặc payload không hợp lệ" } }, 409);
    }
    if (resource === "phieu_xuat") {
      const source = state.resources.yeu_cau_san_xuat.find((entry) => entry.id === (record?.yeu_cau_san_xuat_id || body?.yeu_cau_san_xuat_id));
      if (record && role === "nhan_vien" && source?.nhan_vien_duoc_giao_id !== user.id)
        return respond({ error: { message: "Không có quyền" } }, 403);
      if (["PATCH", "DELETE", "PUT"].includes(method) || action === "ve_nhap")
        return respond({ error: { message: "Không có thao tác này" } }, 405);
      if (!rawId && method === "POST") {
        if (role !== "nhan_vien" || source?.nhan_vien_duoc_giao_id !== user.id)
          return respond({ error: { message: "Không có quyền" } }, 403);
        if (Object.keys(body).sort().join(",") !== "loai_phieu,yeu_cau_san_xuat_id" ||
          !["xuat_linh_kien", "xuat_thanh_pham"].includes(body.loai_phieu))
          return respond({ error: { message: "Payload không đúng hợp đồng" } }, 422);
        const completed = state.resources.chung_tu_hoan_thanh_sx.find((entry) => entry.yeu_cau_san_xuat_id === source.id);
        if (source.trang_thai !== "dang_thuc_hien" || (body.loai_phieu === "xuat_linh_kien"
          ? !(source.so_luong_can_san_xuat > 0)
          : source.loai_yeu_cau !== "xuat_giao" || !(source.so_luong_can_san_xuat === 0 || completed?.trang_thai === "da_duyet")))
          return respond({ error: { message: "Yêu cầu chưa đủ điều kiện lập phiếu" } }, 409);
        if (records.some((entry) => entry.yeu_cau_san_xuat_id === source.id && entry.loai_phieu === body.loai_phieu))
          return respond({ error: { message: "Yêu cầu đã có phiếu xuất loại này" } }, 409);
        const nextId = Math.max(0, ...records.map((entry) => entry.id)) + 1;
        const created = { id: nextId, ma_phieu_xuat: `PX-FIXTURE-${nextId}`, ...body, nhan_vien_id: user.id,
          trang_thai: "nhap", created_at: now, updated_at: now, gui_at: null, ly_do_tu_choi: null, phien_ban: 1, tong_tien: null,
          chi_tiet: [{ id: nextId, mat_hang_id: body.loai_phieu === "xuat_linh_kien" ? 1 : source.mat_hang_id,
            so_luong: body.loai_phieu === "xuat_linh_kien" ? source.so_luong_can_san_xuat : source.so_luong,
            don_gia_thuc: null, tong_gia: null }] };
        records.push(created);
        return respond({ data: created, meta: {} }, 201, { etag: '"v1"' });
      }
      if (method === "POST" && action) {
        if ((action === "gui" && role !== "nhan_vien") || (["duyet", "tu_choi"].includes(action) && role !== "quan_ly"))
          return respond({ error: { message: "Không có quyền" } }, 403);
        if (action === "gui" && (Object.keys(body).length || !["nhap", "tu_choi"].includes(record?.trang_thai)))
          return respond({ error: { message: "Trạng thái hoặc payload không hợp lệ" } }, 409);
      }
    }
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
      if ((resource === "phieu_xuat" || resource === "chung_tu_hoan_thanh_sx") && role === "nhan_vien") {
        return respond({ error: { message: "Không có quyền truy cập danh sách" } }, 403);
      }
      const foldSearch = (value) => String(value).trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d");
      let matching = records.filter((entry) =>
        !(resource === "yeu_cau_san_xuat" && role === "nhan_vien" &&
          (entry.trang_thai === "nhap" || entry.nhan_vien_duoc_giao_id !== user.id)) &&
        Object.entries(call.params).every(([key, value]) =>
          key === "bo_thao_tac"
            ? entry.thao_tac !== value
            : ["page", "page_size", "sort", "sort_by", "sort_order"].includes(key) ||
                ["q", "search"].includes(key)
              ? !["q", "search"].includes(key) ||
                (resource === "yeu_cau_san_xuat"
                  ? [entry.ma_yeu_cau_san_xuat, items.find((item) => item.id === entry.mat_hang_id)?.ten_mat_hang || ""]
                    .some((text) => foldSearch(text).includes(foldSearch(value)))
                  : JSON.stringify(entry).toLowerCase().includes(value.toLowerCase()))
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
    }
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
    if (resource === "chung_tu_hoan_thanh_sx" && action === "gui") record.finish_time = now;
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
