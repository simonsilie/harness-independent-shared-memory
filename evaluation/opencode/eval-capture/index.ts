// Evaluation evidence capture for the phase 1A OpenCode client check.
// Records, project-locally and only for `memory-eval` / `memory-startup` agent
// sessions, the effective tool snapshot sent to the model and every tool
// execution with its raw arguments, result, and timestamps.
import { Plugin } from "@opencode/plugin"
import { appendFileSync, existsSync, mkdirSync } from "node:fs"
import { join } from "node:path"

const TRACKED_AGENTS = new Set(["memory-eval", "memory-startup"])
const ALLOWED_TOOLS = new Set(["basic_memory_bm_search", "basic_memory_bm_read"])

export default Plugin.define({
  id: "eval-capture",
  async setup(ctx) {
    const root = ctx.location.directory
    const dirs = new Map<string, string>()
    const agents = new Map<string, string>()
    const snapshots = new Set<string>()

    function dirFor(sessionID: string): string {
      let dir = dirs.get(sessionID)
      if (!dir) {
        dir = join(root, "evaluation", "opencode", "runs", sessionID)
        mkdirSync(dir, { recursive: true })
        dirs.set(sessionID, dir)
      }
      return dir
    }

    function record(sessionID: string, kind: string, data: Record<string, unknown>) {
      appendFileSync(
        join(dirFor(sessionID), "events.jsonl"),
        JSON.stringify({ time: new Date().toISOString(), kind, ...data }) + "\n",
      )
    }

    async function agentOf(sessionID: string): Promise<string> {
      let agent = agents.get(sessionID)
      if (agent === undefined) {
        const info = await ctx.session.get({ sessionID })
        agent = (info as { agent?: string }).agent
        if (!agent || agent === "unknown") throw new Error("Cannot establish session agent")
        agents.set(sessionID, agent)
      }
      return agent
    }

    await ctx.tool.hook("execute.before", async (event) => {
      const e = event as any
      const sessionID = e.sessionID
      if (!sessionID) throw new Error("Missing session ID")
      if (!(TRACKED_AGENTS.has(await agentOf(sessionID)))) return
      if (!ALLOWED_TOOLS.has(e.tool)) throw new Error(`Tool outside evaluation allowlist: ${e.tool}`)
      record(sessionID, "tool.execute.before", {
        eventKeys: Object.keys(e),
        callID: e.callID ?? e.id,
        tool: e.tool,
        input: e.input,
      })
    })

    await ctx.tool.hook("execute.after", async (event) => {
      const e = event as any
      const sessionID = e.sessionID
      if (!sessionID) throw new Error("Missing session ID")
      if (!(TRACKED_AGENTS.has(await agentOf(sessionID)))) return
      record(sessionID, e.status === "error" ? "tool.execute.error" : "tool.execute.completed", {
        eventKeys: Object.keys(e),
        callID: e.callID ?? e.id,
        tool: e.tool,
        result: e.result,
        error: e.error ? String(e.error) : undefined,
      })
    })

    await ctx.session.hook("context", async (event) => {
      const e = event as any
      const sessionID = e.sessionID
      if (!sessionID) throw new Error("Missing session ID")
      if (!(TRACKED_AGENTS.has(await agentOf(sessionID)))) return
      // Enforce the tool allowlist on the outgoing model request, mirroring
      // Codex's enabled_tools: only the Basic Memory search/read tools stay.
      let excludedToolNames: string[] | undefined
      if (e.tools && typeof e.tools === "object") {
        excludedToolNames = Object.keys(e.tools).filter((name) => !ALLOWED_TOOLS.has(name))
        for (const name of excludedToolNames) delete e.tools[name]
      }
      const toolNames = e.tools ? Object.keys(e.tools) : undefined
      const mcp = await ctx.mcp.list()
      const connected = mcp.data.some((server: any) => server.name === "basic_memory" && server.status.status === "connected")
      if (!connected || !toolNames || toolNames.length !== 2 || toolNames.some((name) => !ALLOWED_TOOLS.has(name))) {
        record(sessionID, "request.rejected", { toolNames, excludedToolNames, mcp })
        throw new Error("Incomplete evaluation tool inventory or disconnected Basic Memory")
      }
      record(sessionID, "request.context", {
        eventKeys: Object.keys(e),
        agent: e.agent,
        model: e.model,
        toolNames,
        excludedToolNames,
      })
      // The full system/tools snapshot plus MCP connection state is saved
      // once per session; later steps record only the tool names above.
      if (!snapshots.has(sessionID)) {
        record(sessionID, "request.context.snapshot", {
          tools: e.tools ?? undefined,
          system: Array.isArray(e.system)
            ? e.system.map((part: any) => (part && typeof part === "object" ? part.text : part))
            : e.system,
          instructions: e.metadata?.experimental?.instructions,
          mcp,
        })
        snapshots.add(sessionID)
      }
      if (existsSync(join(dirFor(sessionID), "preflight-request.json"))) {
        record(sessionID, "request.preflight", { toolNames })
        throw new Error("Evaluation preflight complete; model request stopped")
      }
    })
  },
})
