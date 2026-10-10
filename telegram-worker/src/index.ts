interface Env {
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_WEBHOOK_SECRET: string;
  TELEGRAM_ALLOWED_USER_ID: string;
  DB: D1Database;
}
interface D1Database {
  prepare(query: string): D1PreparedStatement;
  batch(statements: D1PreparedStatement[]): Promise<unknown[]>;
}
interface D1PreparedStatement {
  bind(...values: unknown[]): D1PreparedStatement;
  first<T = Record<string, unknown>>(): Promise<T | null>;
  all<T = Record<string, unknown>>(): Promise<{ results: T[] }>;
  run(): Promise<unknown>;
}
type TelegramMessage = { message_id: number; date: number; text?: string; chat: { id: number; type: string }; from?: { id: number; is_bot?: boolean } };
type Update = { update_id: number; message?: TelegramMessage; callback_query?: { id: string; from: { id: number }; message?: TelegramMessage; data?: string } };
type Task = { id: number; title: string; done: number; priority: number; created_at: string };

const schema = [
  "CREATE TABLE IF NOT EXISTS processed_updates (update_id INTEGER PRIMARY KEY, processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, chat_id TEXT NOT NULL, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, priority INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE INDEX IF NOT EXISTS tasks_user_status ON tasks(user_id, done, priority, id)",
  "CREATE TABLE IF NOT EXISTS preferences (user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, key))"
];

function response(body: string, status = 200): Response {
  return new Response(body, { status, headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" } });
}
function equalSecret(a: string, b: string): boolean {
  if (!a || !b || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
async function telegram(env: Env, method: string, payload: Record<string, unknown>): Promise<any> {
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload)
  });
  if (!r.ok) throw new Error(`Telegram API HTTP ${r.status}`);
  const data: any = await r.json();
  if (!data.ok) throw new Error("Telegram API rejected request");
  return data.result;
}
async function send(env: Env, chatId: number, text: string, replyMarkup?: unknown): Promise<void> {
  const payload: Record<string, unknown> = { chat_id: chatId, text: text.slice(0, 4000), disable_web_page_preview: true };
  if (replyMarkup) payload.reply_markup = replyMarkup;
  await telegram(env, "sendMessage", payload);
}
const keyboard = (rows: unknown[][]) => ({ inline_keyboard: rows });
async function init(env: Env): Promise<void> {
  await env.DB.batch(schema.map(statement => env.DB.prepare(statement)));
}
async function taskList(env: Env, userId: string): Promise<Task[]> {
  const r = await env.DB.prepare("SELECT id, title, done, priority, created_at FROM tasks WHERE user_id = ? ORDER BY done ASC, priority DESC, id DESC LIMIT 10").bind(userId).all<Task>();
  return r.results;
}

const EVIDENCE_BASE = "https://raw.githubusercontent.com/DrRomanSalvador/coalicion/main/";
type JsonEvidence = Record<string, any>;
async function readEvidence(path: string): Promise<JsonEvidence> {
  const response = await fetch(EVIDENCE_BASE + path, { headers: { accept: "application/json" }, signal: AbortSignal.timeout(6000) });
  if (!response.ok) throw new Error("Evidence fetch failed");
  const value: unknown = await response.json();
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Evidence shape invalid");
  return value as JsonEvidence;
}
async function readProductEvidence(): Promise<{observations: JsonEvidence; situation: JsonEvidence; coverage: JsonEvidence; monitor: JsonEvidence}> {
  const [observations, situation, coverage, monitor] = await Promise.all([
    readEvidence("artifacts/estimation/observations.json"),
    readEvidence("artifacts/situation_state.json"),
    readEvidence("ci_evidence/poll_source_coverage.json"),
    readEvidence("artifacts/poll_monitor_state.json")
  ]);
  if (observations.schema !== "REAL_ESTIMATION_OBSERVATIONS_V1" || situation.schema !== "COALICION_SITUATION_STATE_V1" || coverage.schema !== "POLL_SOURCE_COVERAGE_V1" || monitor.schema !== "POLL_MONITOR_STATE_V3") throw new Error("Evidence contract mismatch");
  return {observations, situation, coverage, monitor};
}
function printableNumber(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : "n/d";
}
function evidenceAge(value: unknown): string {
  if (typeof value !== "string" || !Number.isFinite(Date.parse(value))) return "antigüedad no verificable";
  const ageMs = Date.now() - Date.parse(value);
  if (ageMs < -300000) return "fecha futura; revisar";
  const hours = Math.floor(Math.max(0, ageMs) / 3600000);
  return hours >= 24 ? "desactualizada (" + Math.floor(hours / 24) + " días)" : "actualizada hace " + hours + " h";
}
async function productReply(env: Env, msg: TelegramMessage, command: string, arg: string, userId: string): Promise<void> {
  const chatId = msg.chat.id;
  let data: Awaited<ReturnType<typeof readProductEvidence>>;
  try { data = await readProductEvidence(); } catch {
    await send(env, chatId, "⛔ EVIDENCIA NO VERIFICABLE\nNo se pudo leer o validar la evidencia materializada de COALICIÓN. No se mostrarán cifras electorales inferidas. Reintenta cuando se recupere la fuente.");
    return;
  }
  const {observations: obs, situation: sit, coverage, monitor} = data;
  const polls = Array.isArray(obs.polls) ? obs.polls.filter((p: any) => p && typeof p === "object") : [];
  const counts = sit.counts && typeof sit.counts === "object" ? sit.counts : {};
  const health = sit.source_health && typeof sit.source_health === "object" ? sit.source_health : {};
  const asOf = sit.as_of || obs.generated_at;
  if (command === "/encuestas") {
    const matched = (arg ? polls.filter((p: any) => JSON.stringify(p).toLowerCase().includes(arg.toLowerCase()) : polls).slice(0, 8);
    const lines = matched.map((p: any) => {
      const parties = p.parties && typeof p.parties === "object"
        ? Object.entries(p.parties).filter((e): e is [string, number] => typeof e[1] === "number" && Number.isFinite(e[1])).sort((a,b) => b[1]-a[1]).slice(0,5).map(([name, value]) => name + " " + value.toFixed(1) + "%").join(" · ")
        : "porcentajes no disponibles";
      return "• " + String(p.publication_date || "fecha n/d") + " · " + String(p.pollster || p.source_id || "fuente n/d") + "\n  " + parties + "\n  Clasificación: " + String(p.validation || p.source_tier || "no clasificada") + "\n  " + String(p.source_url || "URL n/d");
    });
    await send(env, chatId, "📊 ENCUESTAS MATERIALIZADAS\nCorte: " + String(asOf || "n/d") + " · " + evidenceAge(asOf) + "\nNacionales: " + printableNumber(obs.national_poll_count) + " · territoriales: " + printableNumber(obs.territorial_poll_count) + "\n\n" + (lines.length ? lines.join("\n\n") : "Sin observaciones coincidentes.") + "\n\nLos porcentajes nacionales no se transforman en escaños ni en estimaciones territoriales.");
    return;
  }
  if (command === "/fuentes") {
    const unhealthy = Array.isArray(coverage.unhealthy_primary_sources) ? coverage.unhealthy_primary_sources : [];
    const stale = Array.isArray(coverage.stale_or_unverified_primary_sources) ? coverage.stale_or_unverified_primary_sources : [];
    const last = coverage.last_runtime_coverage || {};
    const monitorCount = Object.keys(monitor.poll_hashes || {}).length;
    await send(env, chatId, "🛰️ SALUD DE FUENTES\nEstado de cobertura: " + String(coverage.status || "n/d") + " · alcance: " + String(coverage.scope || "n/d") + "\nFuentes configuradas: " + printableNumber(coverage.configured_sources) + " · primarias: " + printableNumber(coverage.primary_sources) + " · sanas: " + printableNumber(coverage.healthy_primary_sources) + "\nComprobaciones registradas: " + printableNumber(last.sources_checked) + " · encuestas con hash en el monitor: " + monitorCount + "\nPrimarias con incidencias: " + (unhealthy.length ? unhealthy.map(String).join(", ") : "ninguna registrada") + "\nPrimarias obsoletas/no verificadas: " + (stale.length ? stale.map(String).join(", ") : "ninguna registrada") + "\n\nLímite: cobertura de transporte no equivale a una encuesta validada de cada encuestadora.");
    return;
  }
  if (command === "/escanos") {
    let prediction: JsonEvidence;
    try { prediction = await readEvidence("artifacts/territorial_prediction_20261008.json"); } catch {
      await send(env, chatId, "⛔ ESCAÑOS BLOQUEADOS\nNo se puede verificar el artefacto territorial. No se publica ningún reparto.");
      return;
    }
    const valid = prediction.status === "PASS" && prediction.policy?.fail_closed === true && prediction.policy?.national_to_territorial_inference === false && prediction.seat_total === 350 && prediction.constituencies && Object.keys(prediction.constituencies).length === 52;
    if (!valid) {
      const blockers = Array.isArray(prediction.blockers) ? prediction.blockers.map(String) : ["Contrato territorial incompleto."];
      await send(env, chatId, "🗳️ ESCAÑOS · CÁLCULO BLOQUEADO\nEstado observado: " + String(prediction.status || "n/d") + " · evidencia territorial: " + printableNumber(prediction.observed_territorial_polls) + "\n\nBloqueos:\n• " + blockers.join("\n• ") + "\n\nNo se extrapolan porcentajes nacionales ni encuestas autonómicas a las 52 circunscripciones.");
      return;
    }
    await send(env, chatId, "🗳️ ESCAÑOS\nLa matriz territorial declara 52 circunscripciones y 350 escaños. Consulta el artefacto reproducible para el detalle por circunscripción.");
    return;
  }
  if (command === "/buscar") {
    const matches = polls.filter((p: any) => JSON.stringify(p).toLowerCase().includes(arg.toLowerCase())).slice(0,5);
    const tasks = await env.DB.prepare("SELECT id,title,done,priority FROM tasks WHERE user_id=? AND title LIKE ? ORDER BY done ASC,priority DESC LIMIT 5").bind(userId, "%" + arg.slice(0,100) + "%").all<Task>();
    const lines = [...matches.map((p: any) => "📊 " + String(p.publication_date || "fecha n/d") + " · " + String(p.pollster || p.source_id || "encuesta") + " · " + String(p.source_url || "URL n/d")), ...tasks.results.map(t => "📋 #" + t.id + " " + (t.done ? "completada" : "pendiente") + " · " + t.title)];
    await send(env, chatId, "🔎 EVIDENCIA Y TAREAS: " + arg + "\n\n" + (lines.length ? lines.join("\n") : "Sin coincidencias en la evidencia materializada ni en las tareas."));
    return;
  }
  const changed = Array.isArray(sit.headline?.changed) ? sit.headline.changed : [];
  const uncertainties = Array.isArray(sit.headline?.uncertainties) ? sit.headline.uncertainties : [];
  const questions = Array.isArray(sit.headline?.questions) ? sit.headline.questions : [];
  const lines = ["🧭 COALICIÓN · SALA DE SITUACIÓN", "Radar: " + String(sit.radar || "n/d"), "Corte: " + String(asOf || "n/d") + " · " + evidenceAge(asOf), "Encuestas nacionales: " + printableNumber(counts.national_polls) + " · territoriales: " + printableNumber(counts.territorial_polls), "Última publicación: " + String(counts.latest_poll_date || "n/d"), "Fuentes primarias sanas: " + printableNumber(health.healthy_primary) + "/" + printableNumber(health.primary), "", "CAMBIOS OBSERVADOS", ...(changed.length ? changed.slice(0,4).map((v: any) => "• " + String(v.party || v.type || "cambio") + (typeof v.delta_pp === "number" ? " " + (v.delta_pp > 0 ? "+" : "") + v.delta_pp.toFixed(1) + " pp" : "") + " · " + String(v.latest_poll_date || "")) : ["• Sin cambios comparables materializados."]), "", "INCERTIDUMBRES / BLOQUEOS", ...(uncertainties.length ? uncertainties.slice(0,4).map((v: any) => "• " + String(v.statement || v.code || "incertidumbre")) : ["• No hay incertidumbres registradas en el resumen materializado."]), "", "No se publican escaños sin matriz territorial general validada."];
  if (command === "/urgente") {
    const high = uncertainties.filter((v: any) => String(v.severity || "").toUpperCase() === "HIGH");
    lines.splice(0, lines.length, "🚨 COALICIÓN · ATENCIÓN PRIORITARIA", "Corte: " + String(asOf || "n/d") + " · " + evidenceAge(asOf), "", ...(high.length ? high.map((v: any) => "• " + String(v.statement || v.code || "bloqueo")) : ["• No constan bloqueos HIGH en la evidencia materializada."]), "", "Encuestas nacionales: " + printableNumber(counts.national_polls) + " · territoriales: " + printableNumber(counts.territorial_polls));
  }
  if (questions.length && command !== "/urgente") lines.push("", "PREGUNTAS DE CONTROL", ...questions.slice(0,2).map((v: any) => "• " + String(v.question || v.id || "pregunta")));
  await send(env, chatId, lines.join("\n"), keyboard([[{text:"📊 Encuestas",callback_data:"cmd:encuestas"},{text:"🛰️ Fuentes",callback_data:"cmd:fuentes"}],[{text:"🗳️ Escaños",callback_data:"cmd:escanos"},{text:"🚨 Urgente",callback_data:"cmd:urgente"}],[{text:"📋 Tareas",callback_data:"task:list"},{text:"❓ Ayuda",callback_data:"cmd:ayuda"}]]));
}
async function handleMessage(env: Env, msg: TelegramMessage): Promise<void> {
  if (!msg.from || msg.from.is_bot || msg.from.id.toString() !== env.TELEGRAM_ALLOWED_USER_ID) return;
  const text = (msg.text || "").trim();
  const chatId = msg.chat.id;
  const userId = String(msg.from.id);
  const command = text.split(/\s+/, 1)[0].split("@")[0].toLowerCase();
  const separator = text.indexOf(" ");
  const arg = separator >= 0 ? text.slice(separator + 1).trim() : "";
  if (command === "/start") {
    await send(env, chatId, "🐝 COALICIÓN · Centro de mando\n\nWebhook seguro activo y tareas con persistencia. El análisis electoral completo sigue en el motor COALICIÓN; este servicio gestiona la interfaz y el estado del despacho.", keyboard([[{text:"🧭 Situación",callback_data:"cmd:hoy"},{text:"🚨 Urgente",callback_data:"cmd:urgente"}],[{text:"📊 Encuestas",callback_data:"cmd:encuestas"},{text:"🛰️ Fuentes",callback_data:"cmd:fuentes"}],[{text:"🗳️ Escaños",callback_data:"cmd:escanos"},{text:"📋 Tareas",callback_data:"task:list"}],[{text:"⚙️ Configuración",callback_data:"cmd:config"},{text:"❓ Ayuda",callback_data:"cmd:ayuda"}]]));
  } else if (command === "/ayuda" || command === "/help") {
    await send(env, chatId, "Comandos disponibles:\n/situacion · /hoy · /resumen · /urgente\n/encuestas [texto] · /fuentes · /escanos · /buscar texto\n/tarea texto · /tarea · /config · /ayuda\n\nLos informes electorales consultan evidencia materializada y bloquean cifras no verificables.");
  } else if (command === "/tarea") {
    if (!arg) {
      const tasks = await taskList(env, userId);
      if (!tasks.length) return send(env, chatId, "No hay tareas. Crea una con /tarea texto de la tarea");
      const rows = tasks.map(t => [{text:`${t.done ? "✅" : t.priority ? "🔴" : "▫️"} ${t.title.slice(0,48)}`,callback_data:`task:open:${t.id}`}]);
      return send(env, chatId, "📋 TAREAS\n" + tasks.map(t => `${t.done ? "✅" : t.priority ? "🔴" : "▫️"} #${t.id} ${t.title}`).join("\n"), keyboard(rows));
    }
    if (arg.length > 500) return send(env, chatId, "La tarea supera el máximo de 500 caracteres.");
    await env.DB.prepare("INSERT INTO tasks(user_id, chat_id, title) VALUES(?,?,?)").bind(userId, String(chatId), arg).run();
    await send(env, chatId, "✅ Tarea guardada de forma persistente:\n" + arg, keyboard([[{text:"Ver tareas",callback_data:"task:list"}]]));
  } else if (command === "/buscar") {
    if (!arg) return send(env, chatId, "Uso: /buscar texto. Busca en encuestas materializadas y tareas persistentes.");
    return productReply(env, msg, command, arg, userId);
  } else if (command === "/config") {
    const row = await env.DB.prepare("SELECT value FROM preferences WHERE user_id=? AND key='muted'").bind(userId).first<{value:string}>();
    const muted = row?.value === "1";
    await send(env, chatId, "⚙️ PREFERENCIAS\nPreferencia guardada en el webhook: alertas " + (muted ? "silenciadas" : "activas") + ".\nEsta preferencia aún no cambia la configuración del motor Python.", keyboard([[{text:muted?"🔔 Activar alertas":"🔕 Silenciar alertas",callback_data:"pref:toggle-muted"}]]));
  } else if (["/situacion", "/hoy", "/resumen", "/urgente", "/encuestas", "/fuentes", "/escanos"].includes(command)) {
    return productReply(env, msg, command === "/hoy" || command === "/resumen" ? "/situacion" : command, arg, userId);
  } else {
    await send(env, chatId, "No reconozco ese comando. Usa /ayuda.");
  }
}
async function handleCallback(env: Env, update: Update): Promise<void> {
  const cb = update.callback_query!;
  if (cb.from.id.toString() !== env.TELEGRAM_ALLOWED_USER_ID || !cb.message) return;
  await telegram(env, "answerCallbackQuery", { callback_query_id: cb.id });
  const chatId = cb.message.chat.id;
  const userId = String(cb.from.id);
  const data = cb.data || "";
  if (["cmd:hoy", "cmd:urgente", "cmd:config", "cmd:ayuda", "cmd:encuestas", "cmd:fuentes", "cmd:escanos"].includes(data)) {
    const command = data.slice(4);
    return handleMessage(env, {...cb.message, text:"/"+command, from:cb.from});
  }
  if (data === "task:list") return handleMessage(env, {...cb.message, text:"/tarea", from:cb.from});
  if (data === "pref:toggle-muted") {
    const row = await env.DB.prepare("SELECT value FROM preferences WHERE user_id=? AND key='muted'").bind(userId).first<{value:string}>();
    const next = row?.value === "1" ? "0" : "1";
    await env.DB.prepare("INSERT INTO preferences(user_id,key,value,updated_at) VALUES(?,'muted',?,CURRENT_TIMESTAMP) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP").bind(userId,next).run();
    return send(env,chatId,"Preferencia del webhook guardada: alertas "+(next==="1"?"silenciadas.":"activadas.")+" Esta acción aún no modifica la configuración de alertas del motor Python.");
  }
  const match = /^task:open:(\d+)$/.exec(data);
  if (match) {
    const id = Number(match[1]);
    const task = await env.DB.prepare("SELECT id,title,done,priority FROM tasks WHERE id=? AND user_id=?").bind(id,userId).first<Task>();
    if (!task) return send(env,chatId,"La tarea ya no existe o no tienes acceso.");
    return send(env,chatId,`Tarea #${task.id}: ${task.title}\nEstado: ${task.done?"completada":"pendiente"}\nPrioridad: ${task.priority?"alta":"normal"}`,keyboard([[{text:task.done?"↩️ Reabrir":"✅ Completar",callback_data:`task:done:${id}`},{text:task.priority?"⬇️ Prioridad normal":"🔴 Alta prioridad",callback_data:`task:priority:${id}`}],[{text:"📋 Volver",callback_data:"task:list"}]]));
  }
  const action = /^task:(done|priority):(\d+)$/.exec(data);
  if (action) {
    const id = Number(action[2]);
    if (action[1] === "done") await env.DB.prepare("UPDATE tasks SET done=1-done,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?").bind(id,userId).run();
    else await env.DB.prepare("UPDATE tasks SET priority=1-priority,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?").bind(id,userId).run();
    return handleMessage(env,{...cb.message,text:"/tarea",from:cb.from});
  }
}
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") return response("ok");
    if (request.method !== "POST" || url.pathname !== "/telegram/webhook") return response("not found",404);
    if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_WEBHOOK_SECRET || !env.TELEGRAM_ALLOWED_USER_ID || !env.DB) return response("service not configured",503);
    const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token") || "";
    if (!equalSecret(secret,env.TELEGRAM_WEBHOOK_SECRET)) return response("unauthorized",401);
    let update: Update;
    try { update = await request.json() as Update; } catch { return response("invalid JSON",400); }
    if (!Number.isSafeInteger(update.update_id)) return response("invalid update",400);
    const senderId = update.message?.from?.id ?? update.callback_query?.from?.id;
    if (senderId === undefined || String(senderId) !== env.TELEGRAM_ALLOWED_USER_ID) return response("ignored");
    try {
      await init(env);
      const inserted = await env.DB.prepare("INSERT OR IGNORE INTO processed_updates(update_id) VALUES(?)").bind(update.update_id).run() as {meta?:{changes?:number}};
      if (inserted.meta?.changes === 0) return response("duplicate");
      if (update.message) await handleMessage(env,update.message);
      else if (update.callback_query) await handleCallback(env,update);
      await env.DB.prepare("DELETE FROM processed_updates WHERE processed_at < datetime('now','-7 days')").run();
      return response("ok");
    } catch {
      // Release the idempotency claim on failure so Telegram can retry the update.
      try { await env.DB.prepare("DELETE FROM processed_updates WHERE update_id = ?").bind(update.update_id).run(); } catch { /* preserve the original failure */ }
      // A 500 response lets Telegram retry transient failures; no internals or tokens are returned.
      return response("temporary processing failure",500);
    }
  }
};
