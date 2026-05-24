import type { Plugin } from "@opencode-ai/plugin"

export const ValidateJsonPlugin: Plugin = async ({ $ }) => {
  return {
    "tool.execute.after": async (input) => {
      const filePath: string =
        input.args?.file_path || input.args?.filePath || ""
      if (!filePath) return

      if (!/\/articles\/.*\.json$/.test(filePath)) return

      if (input.tool !== "write" && input.tool !== "edit") return

      try {
        await $.nothrow`python3 hooks/validate_json.py ${filePath}`
      } catch {
        // 未捕获异常会阻塞 Agent，静默处理
      }
    },
  }
}
