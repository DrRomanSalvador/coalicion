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
  for (const statement of schema) await env.DB.prepare(statement).run();
}
async function taskList(env: Env, userId: string): Promise<Task[]> {
  const r = await env.DB.prepare("SELECT id, title, done, priority, created_at FROM tasks WHERE user_id = ? ORDER BY done ASC, priority DESC, id DESC LIMIT 10").bind(userId).all<Task>();
  return r.results;
}
async function handleMessage(env: Env, msg: TelegramMessage): Promise<void> {
  if (!msg.from || msg.from.is_bot || msg.from.id.toString() !== env.TELEGRAM_ALLOWED_USER_ID) return;
  const text = (msg.text || "").trim();
  const chatId = msg.chat.id;
  const userId = String(msg.from.id);
  const command = text.split(/\s+/, 1)[0].split("@")[0].toLowerCase();
  const arg = text.slice(text.indexOf(" ") + 1).trim();
  if (command === "/start") {
    await send(env, chatId, "🐝 COALICIÓN · Centro de mando\n\nWebhook seguro activo y tareas con persistencia. El análisis electoral completo sigue en el motor COALICIÓN; este servicio gestiona la interfaz y el estado del despacho.", keyboard([[{text:"📍 Hoy",callback_data:"cmd:hoy"},{text:"🚨 Urgente",callback_data:"cmd:urgente"}],[{text:"📋 Tareas",callback_data:"task:list"},{text:"⚙️ Configuración",callback_data:"cmd:config"}],[{text:"❓ Ayuda",callback_data:"cmd:ayuda"}]]));
  } else if (command === "/ayuda" || command === "/help") {
    await send(env, chatId, "Comandos disponibles:\n/hoy · /urgente · /resumen · /buscar texto\n/tarea texto · /tarea · /config · /ayuda\n\nLos botones permiten completar tareas y cambiar su prioridad. Acceso restringido al operador autorizado.");
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
    if (!arg) return send(env, chatId, "Uso: /buscar texto. Busca en tus tareas persistentes; la búsqueda de evidencia electoral materializada se habilitará cuando se conecte el índice del motor.");
    const results = await env.DB.prepare("SELECT id,title,done,priority FROM tasks WHERE user_id=? AND title LIKE ? ORDER BY done ASC,priority DESC LIMIT 8").bind(userId, `%${arg.slice(0,100)}%`).all<Task>();
    await send(env, chatId, results.results.length ? "🔎 Tareas coincidentes:\n" + results.results.map(t=>`#${t.id} ${t.done?"✅":"▫️"} ${t.title}`).join("\n") : "No hay tareas coincidentes.");
  } else if (command === "/config") {
    const row = await env.DB.prepare("SELECT value FROM preferences WHERE user_id=? AND key='muted'").bind(userId).first<{value:string}>();
    const muted = row?.value === "1";
    await send(env, chatId, "⚙️ PREFERENCIAS\nAlertas informativas: " + (muted ? "silenciadas" : "activas"), keyboard([[{text:muted?"🔔 Activar alertas":"🔕 Silenciar alertas",callback_data:"pref:toggle-muted"}]]));
  } else if (command === "/hoy" || command === "/urgente" || command === "/resumen") {
    const tasks = await taskList(env, userId);
    const pending = tasks.filter(t=>!t.done);
    const urgent = pending.filter(t=>t.priority);
    const title = command === "/urgente" ? "🚨 URGENTE" : command === "/resumen" ? "🗞️ RESUMEN" : "🧭 COALICIÓN · HOY";
    const selected = command === "/urgente" ? urgent : pending;
    await send(env, chatId, title + "\n\n" + (command === "/resumen" ? "Estado del despacho guardado de forma persistente.\n" : "") + `Tareas pendientes: ${pending.length}\nPrioridad alta: ${urgent.length}\n\n` + (selected.length ? selected.map(t=>`${t.priority?"🔴":"▫️"} #${t.id} ${t.title}`).join("\n") : "No hay tareas pendientes en esta categoría.") + "\n\nNota: este parte no afirma disponer de nuevos datos electorales; resume el estado persistente del despacho.", keyboard([[{text:"📋 Gestionar tareas",callback_data:"task:list"}]]));
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
  if (data === "cmd:hoy" || data === "cmd:urgente" || data === "cmd:config" || data === "cmd:ayuda") {
    const command = data.slice(4);
    return handleMessage(env, {...cb.message, text:"/"+command, from:cb.from});
  }
  if (data === "task:list") return handleMessage(env, {...cb.message, text:"/tarea", from:cb.from});
  if (data === "pref:toggle-muted") {
    const row = await env.DB.prepare("SELECT value FROM preferences WHERE user_id=? AND key='muted'").bind(userId).first<{value:string}>();
    const next = row?.value === "1" ? "0" : "1";
    await env.DB.prepare("INSERT INTO preferences(user_id,key,value,updated_at) VALUES(?,'muted',?,CURRENT_TIMESTAMP) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP").bind(userId,next).run();
    return send(env,chatId,"Alertas informativas "+(next==="1"?"silenciadas.":"activadas."));
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
    try {
      await init(env);
      const inserted = await env.DB.prepare("INSERT OR IGNORE INTO processed_updates(update_id) VALUES(?)").bind(update.update_id).run() as {meta?:{changes?:number}};
      if (inserted.meta?.changes === 0) return response("duplicate");
      if (update.message) await handleMessage(env,update.message);
      else if (update.callback_query) await handleCallback(env,update);
      await env.DB.prepare("DELETE FROM processed_updates WHERE processed_at < datetime('now','-7 days')").run();
      return response("ok");
    } catch {
      // A 500 response lets Telegram retry transient failures; no internals or tokens are returned.
      return response("temporary processing failure",500);
    }
  }
};
