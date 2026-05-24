import { describe, expect, it } from "vitest";
import { formatHttpError } from "./httpErrors";

describe("formatHttpError", () => {
  it("maps 405 Method Not Allowed", () => {
    expect(formatHttpError(405, '{"detail":"Method Not Allowed"}')).toBe(
      "接口不可用：请求地址或方法不正确",
    );
  });

  it("formats pydantic validation errors", () => {
    const body = JSON.stringify({
      detail: [
        {
          loc: ["body", "name"],
          msg: "String should have at least 1 character",
          type: "string_too_short",
        },
      ],
    });
    expect(formatHttpError(422, body)).toBe("输入有误：名称不能为空");
  });

  it("formats AI service errors", () => {
    expect(
      formatHttpError(502, '{"detail":"OpenAI 账户额度已用尽，请检查计费/充值"}'),
    ).toBe("AI 服务错误：OpenAI 账户额度已用尽，请检查计费/充值");
  });
});
