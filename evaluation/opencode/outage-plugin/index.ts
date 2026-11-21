// Outage evidence capture for the phase 1A OpenCode client check.
// Unlike the eval-capture plugin, this variant runs with the Basic Memory
// server deliberately failed: it strips every tool from the outgoing model
// request, records what the model was actually sent (including the MCP server
// status), and lets the model respond so its behaviour without the service is
// observed. It never rejects a request.
import { Plugin } from "@opencode/plugin"
import { appendFileSync, mkdirSync } from "node:fs"
import { join } from "node:path"

const TRACKED_AGENTS = new Set(["memory-outage"])

export default Plugin.define({
  id: "eval-outage",
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
      if (!TRACKED_AGENTS.has(await agentOf(sessionID))) return
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
      if (!TRACKED_AGENTS.has(await agentOf(sessionID))) return
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
      if (!TRACKED_AGENTS.has(await agentOf(sessionID))) return
      // The substituted server command fails, so no Basic Memory tool exists;
      // strip every remaining tool from the outgoing request and record the
      // inventory the model would have seen, together with the server status.
      let excludedToolNames: string[] | undefined
      if (e.tools && typeof e.tools === "object") {
        excludedToolNames = Object.keys(e.tools)
        for (const name of excludedToolNames) delete e.tools[name]
      }
      const mcp = await ctx.mcp.list()
      record(sessionID, "request.context", {
        eventKeys: Object.keys(e),
        agent: e.agent,
        model: e.model,
        excludedToolNames,
        mcp,
      })
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
    })
  },
})
