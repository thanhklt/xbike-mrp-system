import axios, { AxiosError } from "axios";
import type { AxiosAdapter, AxiosResponse } from "axios";
import { DemoEngine, DemoError } from "./demo-engine";
import type {
  Receipt,
  ReceiptInput,
  RequestInput,
  ProductionRequest,
  WorkOrder,
  RequestPreview,
  Workspace,
} from "./types";

function bodyObject(value: unknown): Record<string, unknown> {
  const parsed: unknown = typeof value === "string" ? JSON.parse(value) : value;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
    throw new DemoError("Dữ liệu yêu cầu không hợp lệ.");
  return parsed as Record<string, unknown>;
}

// Axios keeps the same request boundary as a real API. This adapter only talks
// to this workspace's in-memory engine; no request reaches the backend.
export function createDemoApi() {
  const engine = new DemoEngine();
  const adapter: AxiosAdapter = async (config) => {
    const response: AxiosResponse = {
      data: undefined,
      status: 200,
      statusText: "OK",
      headers: {},
      config,
    };
    try {
      const url = config.url ?? "";
      if (config.method === "get" && url === "/workspace") response.data = engine.snapshot();
      else if (url === "/reset") response.data = engine.reset();
      else {
        const body = bodyObject(config.data);
        switch (url) {
          case "/receipts/draft":
            response.data = engine.saveReceipt(body as unknown as ReceiptInput);
            break;
          case "/receipts/confirm":
            response.data = engine.confirmReceipt(body as unknown as ReceiptInput);
            break;
          case "/requests":
            response.data = engine.createRequest(body as unknown as RequestInput);
            break;
          case "/requests/update":
            response.data = engine.updateRequest(
              String(body.id),
              body.input as unknown as RequestInput,
            );
            break;
          case "/requests/preview":
            response.data = engine.previewRequest(String(body.id));
            break;
          case "/requests/send":
            response.data = engine.sendRequest(String(body.id), String(body.token));
            break;
          case "/work-orders/assign":
            response.data = engine.assignOrder(
              String(body.id),
              body.assigneeId === null ? null : String(body.assigneeId),
            );
            break;
          case "/work-orders/send":
            response.data = engine.sendOrder(String(body.id));
            break;
          case "/issues/approve":
            response.data = engine.approveIssue(String(body.id));
            break;
          case "/issues/reject":
            response.data = engine.rejectIssue(String(body.id), String(body.reason ?? ""));
            break;
          default:
            throw new DemoError("Không tìm thấy thao tác demo.");
        }
      }
      return response;
    } catch (error) {
      response.status = 422;
      response.statusText = "Validation failed";
      response.data = {
        message: error instanceof Error ? error.message : "Không thể thực hiện thao tác.",
      };
      throw new AxiosError(response.data.message, "ERR_DEMO", config, undefined, response);
    }
  };
  const client = axios.create({ adapter });
  return {
    workspace: async () => (await client.get<Workspace>("/workspace")).data,
    reset: async () => (await client.post<Workspace>("/reset")).data,
    saveReceipt: async (body: ReceiptInput) =>
      (await client.post<Receipt>("/receipts/draft", body)).data,
    confirmReceipt: async (body: ReceiptInput) =>
      (await client.post<Receipt>("/receipts/confirm", body)).data,
    createRequest: async (body: RequestInput) =>
      (await client.post<ProductionRequest>("/requests", body)).data,
    updateRequest: async (body: { id: string; input: RequestInput }) =>
      (await client.post<ProductionRequest>("/requests/update", body)).data,
    previewRequest: async (id: string) =>
      (await client.post<RequestPreview>("/requests/preview", { id })).data,
    sendRequest: async (body: { id: string; token: string }) =>
      (await client.post<ProductionRequest>("/requests/send", body)).data,
    assignOrder: async (body: { id: string; assigneeId: string | null }) =>
      (await client.post<WorkOrder>("/work-orders/assign", body)).data,
    sendOrder: async (id: string) =>
      (await client.post<WorkOrder>("/work-orders/send", { id })).data,
    approveIssue: async (id: string) =>
      (await client.post<Workspace>("/issues/approve", { id })).data,
    rejectIssue: async (body: { id: string; reason: string }) =>
      (await client.post<Workspace>("/issues/reject", body)).data,
  };
}

export type DemoApi = ReturnType<typeof createDemoApi>;
