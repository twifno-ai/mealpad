const STATUS_MESSAGES: Record<number, string> = {
  400: "请求无效",
  404: "未找到",
  405: "接口不可用",
  422: "输入有误",
  500: "服务器错误",
};

const DETAIL_MESSAGES: Record<string, string> = {
  "Method Not Allowed": "请求地址或方法不正确",
  "Not Found": "资源不存在",
  "Invalid recipe type": "食谱类型无效",
  "Recipe not found": "食谱不存在",
};

const FIELD_LABELS: Record<string, string> = {
  name: "名称",
  type: "类型",
  description: "描述",
  ingredients: "食材",
};

function formatValidationItem(item: unknown): string {
  if (typeof item !== "object" || item === null) return String(item);
  const row = item as { loc?: unknown[]; msg?: string };
  const field = row.loc?.[row.loc.length - 1];
  const label = typeof field === "string" ? (FIELD_LABELS[field] ?? field) : "";
  const msg = row.msg ?? "";

  if (msg.includes("at least 1 character")) {
    return label ? `${label}不能为空` : "请填写必填项";
  }
  if (msg.includes("Field required")) {
    return label ? `${label}为必填项` : "缺少必填项";
  }
  return label ? `${label}：${msg}` : msg;
}

function parseDetail(body: string): string | null {
  try {
    const json = JSON.parse(body) as { detail?: unknown };
    const { detail } = json;
    if (typeof detail === "string") {
      return DETAIL_MESSAGES[detail] ?? detail;
    }
    if (Array.isArray(detail)) {
      const parts = detail.map(formatValidationItem).filter(Boolean);
      return parts.length > 0 ? parts.join("；") : null;
    }
  } catch {
    /* plain text body */
  }
  return null;
}

/** Turn an HTTP error response into a user-facing Chinese message. */
export function formatHttpError(status: number, body: string): string {
  const parsed = parseDetail(body.trim());
  const prefix = STATUS_MESSAGES[status] ?? `请求失败 (${status})`;

  if (parsed) {
    return `${prefix}：${parsed}`;
  }
  if (body.trim()) {
    return `${prefix}：${body.trim().slice(0, 200)}`;
  }
  return prefix;
}

export class ApiError extends Error {
  status: number;

  rawBody: string;

  constructor(status: number, body: string) {
    super(formatHttpError(status, body));
    this.name = "ApiError";
    this.status = status;
    this.rawBody = body;
  }
}
