import { describe, it, expect, vi } from "vitest";
import worker from "../src/index";

const env = {
  TELEGRAM_BOT_TOKEN: "test-token",
  TELEGRAM_WEBHOOK_SECRET: "a-secret-value",
  TELEGRAM_ALLOWED_USER_ID: "8459054385",
  DB: {} as any
};

describe("COALICIÓN Telegram webhook", () => {
  it("exposes a minimal health endpoint without secrets", async () => {
    const response = await worker.fetch(new Request("https://worker.test/health"), env as any);
    expect(response.status).toBe(200);
    expect(await response.text()).toBe("ok");
  });
  it("rejects other routes", async () => {
    const response = await worker.fetch(new Request("https://worker.test/"), env as any);
    expect(response.status).toBe(404);
  });
  it("rejects requests without Telegram webhook secret", async () => {
    const response = await worker.fetch(new Request("https://worker.test/telegram/webhook", {method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({update_id:1})}), env as any);
    expect(response.status).toBe(401);
  });
  it("rejects malformed JSON after authentication", async () => {
    const response = await worker.fetch(new Request("https://worker.test/telegram/webhook", {method:"POST",headers:{"X-Telegram-Bot-Api-Secret-Token":env.TELEGRAM_WEBHOOK_SECRET},body:"{"}), env as any);
    expect(response.status).toBe(400);
  });
  it("ignores unauthorized Telegram senders before touching D1", async () => {
    const response = await worker.fetch(new Request("https://worker.test/telegram/webhook", {method:"POST",headers:{"X-Telegram-Bot-Api-Secret-Token":env.TELEGRAM_WEBHOOK_SECRET,"content-type":"application/json"},body:JSON.stringify({update_id:2,message:{message_id:1,date:1,text:"/start",chat:{id:123,type:"private"},from:{id:999,is_bot:false}}})}), env as any);
    expect(response.status).toBe(200);
    expect(await response.text()).toBe("ignored");
  });
  it("answers an authorized /start command through Telegram", async () => {
    const statement = (query: string) => ({
      bind: (..._values: unknown[]) => statement(query),
      first: async () => null,
      all: async () => ({ results: [] }),
      run: async () => ({ meta: { changes: 1 } })
    });
    const mockDb = {
      batch: async () => [],
      prepare: (query: string) => statement(query)
    };
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ok:true,result:{message_id:1}}), {status:200,headers:{"content-type":"application/json"}}));
    vi.stubGlobal("fetch", fetchMock);
    try {
      const response = await worker.fetch(new Request("https://worker.test/telegram/webhook", {
        method:"POST",
        headers:{"X-Telegram-Bot-Api-Secret-Token":env.TELEGRAM_WEBHOOK_SECRET,"content-type":"application/json"},
        body:JSON.stringify({update_id:3,message:{message_id:1,date:1,text:"/start",chat:{id:8459054385,type:"private"},from:{id:8459054385,is_bot:false}}})
      }), {...env,DB:mockDb} as any);
      expect(response.status).toBe(200);
      expect(fetchMock).toHaveBeenCalledOnce();
      const sent = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
      expect(sent.text).toContain("COALICIÓN");
      expect(sent.reply_markup.inline_keyboard.length).toBeGreaterThan(0);
    } finally {
      vi.unstubAllGlobals();
    }
  });
  it("fails closed when secrets are not configured", async () => {
    const response = await worker.fetch(new Request("https://worker.test/telegram/webhook", {method:"POST"}), {DB:{}} as any);
    expect(response.status).toBe(503);
  });
});
