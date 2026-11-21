import { expect, mock, test } from "bun:test"
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { join } from "node:path"

mock.module("@opencode/plugin", () => ({ Plugin: { define: (value: any) => value } }))
const { default: plugin } = await import("./eval-capture/index.ts")

async function fixture(agent: () => Promise<any> = async () => ({ agent: "memory-eval" })) {
  const root = mkdtempSync(join(process.cwd(), ".plugin-test-"))
  const hooks: Record<string, (event: any) => Promise<void>> = {}
  await plugin.setup({
    location: { directory: root },
    session: { get: agent, hook: async (name: string, hook: any) => { hooks[name] = hook } },
    tool: { hook: async (name: string, hook: any) => { hooks[name] = hook } },
    mcp: { list: async () => ({ data: [{ name: "basic_memory", status: { status: "connected" } }] }) },
  } as any)
  return { root, hooks }
}

function context() {
  return { sessionID: "test", system: ["Agent instructions"],
    tools: { basic_memory_bm_search: {}, basic_memory_bm_read: {}, shell: {} } }
}

test("unresolved agent identity stops the outgoing request", async () => {
  for (const agent of [async () => ({}), async () => { throw new Error("lookup failed") }]) {
    const { root, hooks } = await fixture(agent)
    try {
      await expect(hooks.context(context())).rejects.toThrow()
    } finally { rmSync(root, { recursive: true, force: true }) }
  }
})

test("preflight records the restricted inventory and stops before the model", async () => {
  const { root, hooks } = await fixture()
  try {
    const dir = join(root, "evaluation/opencode/runs/test")
    mkdirSync(dir, { recursive: true })
    writeFileSync(join(dir, "preflight-request.json"), "{}")
    const event = context()
    await expect(hooks.context(event)).rejects.toThrow("preflight complete")
    expect(Object.keys(event.tools).sort()).toEqual(["basic_memory_bm_read", "basic_memory_bm_search"])
    const events = readFileSync(join(dir, "events.jsonl"), "utf8").trim().split("\n").map(JSON.parse)
    expect(events.map(e => e.kind)).toContain("request.preflight")
  } finally { rmSync(root, { recursive: true, force: true }) }
})

test("missing required tools stops the outgoing request", async () => {
  const { root, hooks } = await fixture()
  try {
    const event = context()
    delete (event.tools as any).basic_memory_bm_read
    await expect(hooks.context(event)).rejects.toThrow("Incomplete evaluation tool inventory")
  } finally { rmSync(root, { recursive: true, force: true }) }
})

test("execution of a tool outside the allowlist is rejected", async () => {
  const { root, hooks } = await fixture()
  try {
    await expect(hooks["execute.before"]({ sessionID: "test", tool: "shell" })).rejects.toThrow("outside evaluation allowlist")
  } finally { rmSync(root, { recursive: true, force: true }) }
})

test("evidence write failures stop the outgoing request", async () => {
  const { root, hooks } = await fixture()
  try {
    writeFileSync(join(root, "evaluation"), "blocks directory creation")
    await expect(hooks.context(context())).rejects.toThrow()
  } finally { rmSync(root, { recursive: true, force: true }) }
})
