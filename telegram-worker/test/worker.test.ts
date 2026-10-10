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
    function statement(query: string): any {
      return {
        bind: (..._values: unknown[]) => statement(query),
        first: async () => null,
        all: async () => ({ results: [] }),
        run: async () => ({ meta: { changes: 1 } })
      };
    }
    const mockDb = {
      batch: async () => [],
      prepare: (query: string) => statement(query)
    };
    const sentPayloads: Array<{body?: BodyInit | null}> = [];
    vi.stubGlobal("fetch", async (_input: RequestInfo | URL, init?: RequestInit) => { sentPayloads.push({body:init?.body}); return new Response(JSON.stringify({ok:true,result:{message_id:1}}), {status:200,headers:{"content-type":"application/json"}}); });
    try {
      const response = await worker.fetch(new Request("https://worker.test/telegram/webhook", {
        method:"POST",
        headers:{"X-Telegram-Bot-Api-Secret-Token":env.TELEGRAM_WEBHOOK_SECRET,"content-type":"application/json"},
        body:JSON.stringify({update_id:3,message:{message_id:1,date:1,text:"/start",chat:{id:8459054385,type:"private"},from:{id:8459054385,is_bot:false}}})
      }), {...env,DB:mockDb} as any);
      expect(response.status).toBe(200);
      expect(sentPayloads).toHaveLength(1);
      const sent = JSON.parse(String(sentPayloads[0].body));
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

  it("serves the materialized electoral situation and observed changes", async () => {
    const statement = (_query: string): any => ({bind: (..._values: unknown[]) => statement(""), first: async () => null, all: async () => ({results: []}), run: async () => ({meta: {changes: 1}})});
    const mockDb = {batch: async () => [], prepare: (query: string) => statement(query)};
    const sent: any[] = [];
    const fixtures: Record<string, unknown> = {
      "observations.json": {schema:"REAL_ESTIMATION_OBSERVATIONS_V1",national_poll_count:3,territorial_poll_count:0,polls:[{publication_date:"2026-09-23",pollster:"CIS",source_url:"https://www.datoelectoral.es/encuestas",parties:{PSOE:31,PP:25.5}}]},
      "situation_state.json": {schema:"COALICION_SITUATION_STATE_V1",as_of:"2026-10-10T18:27:43+02:00",radar:"UNCERTAINTY",counts:{national_polls:3,territorial_polls:0,latest_poll_date:"2026-09-23"},source_health:{healthy_primary:6,primary:6},headline:{changed:[{party:"PSOE",delta_pp:-2.0,latest_poll_date:"2026-09-23"}],uncertainties:[{severity:"HIGH",statement:"Sin matriz territorial"}],questions:[]}},
      "poll_source_coverage.json": {schema:"POLL_SOURCE_COVERAGE_V1",status:"PASS",scope:"test",configured_sources:16,primary_sources:6,healthy_primary_sources:6,unhealthy_primary_sources:[],stale_or_unverified_primary_sources:[]},
      "poll_monitor_state.json": {schema:"POLL_MONITOR_STATE_V3",poll_hashes:{}}
    };
    vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("raw.githubusercontent.com")) {
        const key = url.split("/").pop() || "";
        return new Response(JSON.stringify(fixtures[key] || {}), {status:200,headers:{"content-type":"application/json"}});
      }
      sent.push(JSON.parse(String(init?.body)));
      return new Response(JSON.stringify({ok:true,result:{message_id:1}}), {status:200,headers:{"content-type":"application/json"}});
    });
    try {
      const response = await worker.fetch(new Request("https://worker.test/telegram/webhook", {method:"POST",headers:{"X-Telegram-Bot-Api-Secret-Token":env.TELEGRAM_WEBHOOK_SECRET,"content-type":"application/json"},body:JSON.stringify({update_id:20,message:{message_id:2,date:1,text:"/situacion",chat:{id:8459054385,type:"private"},from:{id:8459054385,is_bot:false}}})}), {...env,DB:mockDb} as any);
      expect(response.status).toBe(200);
      const reply = sent.find(p => String(p.text).includes("SALA DE SITUACIÓN"));
      expect(reply).toBeTruthy();
      expect(reply.text).toContain("PSOE -2.0 pp");
      expect(reply.text).toContain("Sin matriz territorial");
    } finally { vi.unstubAllGlobals(); }
  });

  it("fails closed when the territorial prediction is blocked", async () => {
    const statement = (_query: string): any => ({bind: (..._values: unknown[]) => statement(""), first: async () => null, all: async () => ({results: []}), run: async () => ({meta: {changes: 1}})});
    const mockDb = {batch: async () => [], prepare: (query: string) => statement(query)};
    const sent: any[] = [];
    const fixtures: Record<string, unknown> = {
      "observations.json": {schema:"REAL_ESTIMATION_OBSERVATIONS_V1",national_poll_count:3,territorial_poll_count:0,polls:[]},
      "situation_state.json": {schema:"COALICION_SITUATION_STATE_V1",as_of:"2026-10-10T18:27:43+02:00",counts:{national_polls:3,territorial_polls:0},source_health:{},headline:{}},
      "poll_source_coverage.json": {schema:"POLL_SOURCE_COVERAGE_V1",status:"PASS"},
      "poll_monitor_state.json": {schema:"POLL_MONITOR_STATE_V3",poll_hashes:{}},
      "territorial_prediction_20261008.json": {schema:"TERRITORIAL_PREDICTION_2026_V2",status:"BLOCKED",observed_territorial_polls:0,seat_total:0,blockers:["BLOCKED_NO_52_CIRCUMSCRIPTION_GENERAL_ELECTION_INPUT"],policy:{fail_closed:true,national_to_territorial_inference:false},constituencies:{}}
    };
    vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("raw.githubusercontent.com")) {
        const key = url.split("/").pop() || "";
        return new Response(JSON.stringify(fixtures[key] || {}), {status:200,headers:{"content-type":"application/json"}});
      }
      sent.push(JSON.parse(String(init?.body)));
      return new Response(JSON.stringify({ok:true,result:{message_id:1}}), {status:200,headers:{"content-type":"application/json"}});
    });
    try {
      const response = await worker.fetch(new Request("https://worker.test/telegram/webhook", {method:"POST",headers:{"X-Telegram-Bot-Api-Secret-Token":env.TELEGRAM_WEBHOOK_SECRET,"content-type":"application/json"},body:JSON.stringify({update_id:21,message:{message_id:3,date:1,text:"/escanos",chat:{id:8459054385,type:"private"},from:{id:8459054385,is_bot:false}}})}), {...env,DB:mockDb} as any);
      expect(response.status).toBe(200);
      const reply = sent.find(p => String(p.text).includes("ESCAÑOS"));
      expect(reply.text).toContain("CÁLCULO BLOQUEADO");
      expect(reply.text).toContain("BLOCKED_NO_52_CIRCUMSCRIPTION_GENERAL_ELECTION_INPUT");
      expect(reply.text).not.toContain("350 escaños repartidos");
    } finally { vi.unstubAllGlobals(); }
  });
});
