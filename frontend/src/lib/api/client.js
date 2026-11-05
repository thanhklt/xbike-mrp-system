import axios from "axios";
import { cleanParams, normalizeResponse, toApiError, versionHeaders } from "./contract.js";

export const TOKEN_KEY = "xbike_access_token";
const configuredBase = import.meta.env?.VITE_API_BASE_URL || "/api/v1";
// Development uses the Vite proxy so the browser can read ETag headers.
const baseURL = import.meta.env?.DEV
  ? new URL(configuredBase, window.location.origin).pathname
  : configuredBase;
export const apiClient = axios.create({
  baseURL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token && !config.url.startsWith("/auth/dang_nhap"))
    config.headers.Authorization = `Bearer ${token}`;
  return config;
});
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === "ERR_CANCELED") return Promise.reject(error);
    const failure = toApiError(error);
    if (
      (failure.status === 401 || failure.code === "tai_khoan_bi_vo_hieu_hoa") &&
      error.config?.headers?.Authorization
    ) {
      window.dispatchEvent(new CustomEvent("xbike:session-ended", { detail: failure.message }));
    }
    return Promise.reject(failure);
  },
);

export async function readResource(path, params, signal) {
  return normalizeResponse(await apiClient.get(path, { params: cleanParams(params), signal }));
}

/** A write uses the ETag the user reviewed, never a freshly fetched version. */
export async function writeResource({ path, method = "post", body = {}, etag, versioned = true }) {
  return normalizeResponse(
    await apiClient.request({
      url: path,
      method,
      data: body,
      headers: versioned ? versionHeaders(etag) : {},
    }),
  );
}

export async function readAll(path, params, signal) {
  const first = await readResource(path, { ...params, page: 1, page_size: 100 }, signal);
  const rows = [...first.data];
  for (let page = 2; page <= first.meta.total_pages; page += 1) {
    const next = await readResource(path, { ...params, page, page_size: 100 }, signal);
    rows.push(...next.data);
  }
  return rows;
}
