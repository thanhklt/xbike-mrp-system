export function cleanParams(params = {}) {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== "" && value !== null && value !== undefined,
    ),
  );
}

export function normalizeResponse(response) {
  const body = response.data;
  const legacy = body?.pagination;
  return {
    data: body?.data ?? null,
    meta: legacy ? { ...legacy, total: legacy.total_items } : (body?.meta ?? {}),
    etag: response.headers?.etag ?? null,
  };
}

export function auditParams(params) {
  const { q, sort, ...rest } = params;
  return cleanParams({
    ...rest,
    search: q,
    sort_by: sort?.replace(/^-/, "") || "created_at",
    sort_order: sort?.startsWith("-") ? "desc" : "asc",
  });
}

export class ApiError extends Error {
  constructor(
    message,
    { status = 0, code, details = [], requestId, ticketId, uncertain = false } = {},
  ) {
    super(message);
    Object.assign(this, { status, code, details, requestId, ticketId, uncertain });
  }
}

export function toApiError(error) {
  if (error instanceof ApiError) return error;
  const body = error.response?.data;
  const failure = body?.error;
  const status = error.response?.status ?? 0;
  const uncertain = !status && error.config?.method !== "get";
  const fallback =
    status === 412
      ? "Dữ liệu đã thay đổi. Tải lại và xác nhận lại trước khi tiếp tục."
      : status === 428
        ? "Chưa có phiên bản dữ liệu. Tải lại chi tiết trước khi tiếp tục."
        : status === 401
          ? "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại."
          : status === 403
            ? "Bạn không có quyền thực hiện thao tác này."
            : status
              ? "Không thể thực hiện yêu cầu. Vui lòng thử lại sau."
              : uncertain
                ? "Mất kết nối khi gửi yêu cầu. Chưa xác định kết quả; hãy tải lại để kiểm tra trước khi thực hiện lại."
                : "Không kết nối được máy chủ. Kiểm tra kết nối và thử tải lại.";
  return new ApiError(
    failure?.message || (typeof body?.detail === "string" ? body.detail : fallback),
    {
      status,
      code: failure?.code,
      details: Array.isArray(failure?.details)
        ? failure.details
        : Array.isArray(body?.detail)
          ? body.detail.map((entry) => ({
              field: entry.loc?.slice(1).join("."),
              reason: entry.msg,
            }))
          : [],
      requestId: body?.meta?.request_id,
      ticketId: failure?.ticket_da_luu ? failure.ticket_id : null,
      uncertain,
    },
  );
}

export function versionHeaders(etag) {
  if (!etag || etag.startsWith("W/") || etag === "*") {
    throw new ApiError(
      "Không đọc được phiên bản dữ liệu. Hãy tải lại chi tiết; nếu vẫn lỗi, kiểm tra cấu hình proxy/ETag.",
      { status: 428 },
    );
  }
  return { "If-Match": etag };
}
