import { expect, mock, test } from "bun:test"
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs"
import { join } from "node:path"

mock.module("@opencode/plugin", () => ({ Plugin: { define: (value: any) => value } }))
const { default: plugin } = await import("./outage-plugin/index.ts")

async function fixture(agent: () => Promise<any> = async () => ({ agent: "memory-outage" })) {
  const root = mkdtempSync(join(process.cwd(), ".plugin-test-"))
  const hooks: Record<string, (event: any) => Promise<void>> = {}
  await plugin.setup({
    location: { directory: root },
    session: { get: agent, hook: async (name: string, hook: any) => { hooks[name] = hook } },
    tool: { hook: async (name: string, hook: any) => { hooks[name] = hook } },
    mcp: { list: async () => ({ data: [{ name: "basic_memory", status: { status: "failed" } }] }) },
  } as any)
  return { root, hooks }
}

function context() {
  return { sessionID: "test", system: ["Agent instructions"],
    tools: { basic_memory_bm_search: {}, shell: {} } }
}

test("outage request is recorded with every tool stripped and never rejected", async () => {
  const { root, hooks } = await fixture()
  try {
    const event = context()
    await hooks.context(event)
    expect(event.tools).toEqual({})
    const dir = join(root, "evaluation/opencode/runs/test")
    const events = readFileSync(join(dir, "events.jsonl"), "utf8").trim().split("\n").map(JSON.parse)
    expect(events.map(e => e.kind)).toEqual(["request.context", "request.context.snapshot"])
    const snapshot = events[1]
    expect(snapshot.mcp.data[0].status.status).toBe("failed")
    expect(snapshot.system).toEqual(["Agent instructions"])
  } finally { rmSync(root, { recursive: true, force: true }) }
})

test("snapshots are recorded once per session", async () => {
  const { root, hooks } = await fixture()
  try {
    await hooks.context(context())
    await hooks.context(context())
    const dir = join(root, "evaluation/opencode/runs/test")
    const events = readFileSync(join(dir, "events.jsonl"), "utf8").trim().split("\n").map(JSON.parse)
    expect(events.filter(e => e.kind === "request.context.snapshot")).toHaveLength(1)
    expect(events.filter(e => e.kind === "request.context")).toHaveLength(2)
  } finally { rmSync(root, { recursive: true, force: true }) }
})

test("tool executions are recorded for the outage agent", async () => {
  const { root, hooks } = await fixture()
  try {
    await hooks["execute.before"]({ sessionID: "test", tool: "basic_memory_bm_search", input: {} })
    await hooks["execute.after"]({ sessionID: "test", tool: "basic_memory_bm_search", status: "error", error: new Error("failed") })
    const dir = join(root, "evaluation/opencode/runs/test")
    const events = readFileSync(join(dir, "events.jsonl"), "utf8").trim().split("\n").map(JSON.parse)
    expect(events.map(e => e.kind)).toEqual(["tool.execute.before", "tool.execute.error"])
  } finally { rmSync(root, { recursive: true, force: true }) }
})

test("untracked agents are ignored", async () => {
  const { root, hooks } = await fixture(async () => ({ agent: "memory-eval" }))
  try {
    await hooks.context(context())
    expect(existsSync(join(root, "evaluation/opencode/runs/test/events.jsonl"))).toBe(false)  } finally { rmSync(root, { recursive: true, force: true }) }
})

test("unresolved agent identity still fails the hook", async () => {
  const { hooks } = await fixture(async () => ({}))
  await expect(hooks.context(context())).rejects.toThrow("Cannot establish session agent")
})
