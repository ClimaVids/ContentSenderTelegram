import { DurableObject } from "cloudflare:workers";

const PUBLIC_HELP = `🤖 ContentSenderTelegram | دستیار انتشار محتوای ClimaVids

محتوای منتخب آب، هواشناسی، اقلیم و محیط‌زیست را برای گروه‌ها و کانال‌هایی که ربات را فعال کرده‌اند منتشر می‌کنم.

🚀 شروع مدیران:
ربات را به گروه یا کانال اضافه و Administrator کنید، سپس /setup را بزنید.

⚙️ فرمان‌های مدیر:
/setup — مشاهده تنظیمات همین مقصد
/posts 1 — روزانه ۱ پست
/posts 2 — روزانه ۲ پست
/posts 3 — روزانه ۳ پست
/times 10:00 — زمان ارسال
/times 10:00 20:00 — دو زمان ارسال
/on — فعال‌سازی ارسال
/off — توقف موقت ارسال

📌 گزارش‌های شبکه و اطلاعات فنی فقط برای مالک ربات قابل مشاهده است.`;

const OWNER_HELP = `🔐 پنل خصوصی مالک ContentSenderTelegram

/status — وضعیت کلی
/report — گزارش کامل
/network — تعداد و نام مقصدها
/logs — لاگ رویدادها و خطاها
/health — سلامت Bot و مقصدها
/test — تست Bot و کانال اصلی، بدون انتشار
/run — درخواست اجرای فوری انتشار

/claim — ثبت اولیه این گفت‌وگوی خصوصی به عنوان مالک`;

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const TZ = "Asia/Tehran";
const OWNER_KEYBOARD = { inline_keyboard: [
  [{ text: "📊 وضعیت کلی", callback_data: "owner:status" }, { text: "📋 گزارش کامل", callback_data: "owner:report" }],
  [{ text: "🌐 شبکه مقصدها", callback_data: "owner:network" }, { text: "🧾 لاگ‌ها", callback_data: "owner:logs" }],
  [{ text: "🩺 سلامت", callback_data: "owner:health" }, { text: "🧪 تست", callback_data: "owner:test" }],
  [{ text: "🚀 انتشار فوری", callback_data: "owner:run" }],
] };

const PUBLIC_KEYBOARD = { inline_keyboard: [
  [{ text: "⚙️ تنظیمات مقصد", callback_data: "dest:setup" }],
  [{ text: "📝 تعداد پست روزانه", callback_data: "dest:posts" }, { text: "⏰ زمان‌بندی", callback_data: "dest:times" }],
  [{ text: "▶️ فعال‌سازی", callback_data: "dest:on" }, { text: "⏸ توقف", callback_data: "dest:off" }],
  [{ text: "❓ راهنما", callback_data: "dest:help" }],
] };

const SETTINGS_KEYBOARD = PUBLIC_KEYBOARD;


function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
}

function text(data, status = 200) {
  return new Response(data, { status, headers: { "content-type": "text/plain; charset=utf-8" } });
}

async function telegram(env, method, payload = {}) {
  const token = (env.TELEGRAM_BOT_TOKEN || "").trim();
  if (!token) throw new Error("TELEGRAM_BOT_TOKEN is not configured");
  const response = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.description || `Telegram ${method} failed`);
  return data.result;
}

async function timingSafeEqualText(a, b) {
  const encoder = new TextEncoder();
  const aa = await crypto.subtle.digest("SHA-256", encoder.encode(a));
  const bb = await crypto.subtle.digest("SHA-256", encoder.encode(b));
  return crypto.subtle.timingSafeEqual(aa, bb);
}

function command(textValue) {
  const parts = String(textValue || "").trim().split(/\s+/);
  if (!parts[0]?.startsWith("/")) return [null, []];
  return [parts[0].split("@", 1)[0].toLowerCase(), parts.slice(1)];
}

function validTimes(values) {
  const out = [];
  for (const value of values) {
    const match = /^(\d{1,2}):(\d{2})$/.exec(value);
    if (!match) continue;
    const h = Number(match[1]);
    const m = Number(match[2]);
    if (h >= 0 && h <= 23 && m >= 0 && m <= 59) out.push(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
  }
  return [...new Set(out)].sort();
}

function defaultDestination(chat, botId) {
  return {
    chat_id: Number(chat.id),
    title: chat.title || chat.username || chat.first_name || String(chat.id),
    username: chat.username || null,
    type: chat.type,
    status: "administrator",
    active: true,
    posts_per_day: 1,
    times: ["20:00"],
    bot_id: botId,
    admin_configured: false,
    added_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

export class BotState extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.ctx.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS kv (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        at TEXT NOT NULL,
        kind TEXT NOT NULL,
        detail TEXT NOT NULL
      );
    `);
  }

  async read(key, fallback = null) {
    const row = this.ctx.storage.sql.exec("SELECT value FROM kv WHERE key = ?", key).toArray()[0];
    if (!row) return fallback;
    try { return JSON.parse(row.value); } catch { return row.value; }
  }

  async write(key, value) {
    this.ctx.storage.sql.exec(
      "INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
      key,
      JSON.stringify(value),
    );
  }

  async event(kind, detail) {
    this.ctx.storage.sql.exec("INSERT INTO events(at,kind,detail) VALUES(?,?,?)", new Date().toISOString(), kind, detail);
    this.ctx.storage.sql.exec("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 200)");
  }

  async destinations() {
    const value = await this.read("destinations", {});
    return value && typeof value === "object" ? value : {};
  }

  async owner() { return await this.read("owner_chat_id", null); }

  async updateDestination(chat, updater) {
    const all = await this.destinations();
    const key = String(chat.id);
    const current = all[key] || defaultDestination(chat, this.env.BOT_ID || null);
    const next = updater({ ...current, updated_at: new Date().toISOString() });
    all[key] = next;
    await this.write("destinations", all);
    return next;
  }

  async processUpdate(update) {
    const msg = update.message || update.channel_post || null;
    const membership = update.my_chat_member || null;

    if (membership) {
      const chat = membership.chat || {};
      const status = membership.new_chat_member?.status || "unknown";
      if (!["group", "supergroup", "channel"].includes(chat.type)) return;
      const all = await this.destinations();
      const key = String(chat.id);
      if (["administrator", "creator"].includes(status)) {
        const previous = all[key] || defaultDestination(chat, this.env.BOT_ID || null);
        previous.title = chat.title || chat.username || previous.title;
        previous.username = chat.username || previous.username || null;
        previous.type = chat.type;
        previous.status = status;
        previous.active = true;
        previous.updated_at = new Date().toISOString();
        all[key] = previous;
        await this.write("destinations", all);
        await this.event("destination_added", JSON.stringify({ chat_id: chat.id, title: previous.title, type: chat.type }));
        if (chat.type !== "channel" && !previous.welcome_sent) {
          try {
            await telegram(this.env, "sendMessage", { chat_id: chat.id, text: `👋 سلام!\n\nربات انتشار محتوای ClimaVids فعال شد.\n\n${PUBLIC_HELP}` });
            previous.welcome_sent = true;
            all[key] = previous;
            await this.write("destinations", all);
          } catch (error) {
            await this.event("welcome_error", String(error.message || error));
          }
        }
      } else if (["left", "kicked"].includes(status) && all[key]) {
        all[key].active = false;
        all[key].status = status;
        all[key].updated_at = new Date().toISOString();
        await this.write("destinations", all);
        await this.event("destination_removed", JSON.stringify({ chat_id: chat.id, status }));
      }
      return;
    }

    const callback = update.callback_query || null;
    if (callback) {
      const callbackChat = callback.message?.chat;
      const callbackId = Number(callback.from?.id || 0);
      if (!callbackChat || callbackChat.type !== "private") {
        try { await telegram(this.env, "answerCallbackQuery", { callback_query_id: callback.id, text: "این منو فقط در گفت‌وگوی خصوصی مالک یا مقصد قابل استفاده است." }); } catch {}
        return;
      }
      const owner = await this.owner();
      const isOwner = owner && String(owner) === String(callbackChat.id) && String(callbackId) === String(owner);
      const data = String(callback.data || "");
      try {
        if (data.startsWith("owner:") && isOwner) {
          const action = data.slice(6);
          if (action === "status" || action === "report") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildReport(), reply_markup: OWNER_KEYBOARD });
          else if (action === "network") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildNetwork(), reply_markup: OWNER_KEYBOARD });
          else if (action === "logs") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildLogs(), reply_markup: OWNER_KEYBOARD });
          else if (action === "health") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildHealth(), reply_markup: OWNER_KEYBOARD });
          else if (action === "test") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildTest(), reply_markup: OWNER_KEYBOARD });
          else if (action === "run") {
            await this.write("force_run", { requested_at: new Date().toISOString(), requested_by: Number(owner) });
            await this.event("manual_run_requested", JSON.stringify({ requested_by: Number(owner), via: "button" }));
            await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: "🚀 درخواست انتشار فوری ثبت شد. در اولین چرخه موتور انتشار اجرا می‌شود.", reply_markup: OWNER_KEYBOARD });
          }
        } else {
          await telegram(this.env, "sendMessage", { chat_id: Number(callbackChat.id), text: PUBLIC_HELP, reply_markup: PUBLIC_KEYBOARD });
        }
        await telegram(this.env, "answerCallbackQuery", { callback_query_id: callback.id });
      } catch (error) {
        try { await telegram(this.env, "answerCallbackQuery", { callback_query_id: callback.id, text: "⚠️ خطا؛ دوباره تلاش کنید." }); } catch {}
        await this.event("callback_error", String(error.message || error));
      }
      return;
    }

    if (!msg?.chat) return;
    const [cmd, args] = command(msg.text);
    if (!cmd) return;
    const chat = msg.chat;
    const chatId = Number(chat.id);

    if (chat.type === "private") {
      const owner = await this.owner();
      if (cmd === "/start") {
        await telegram(this.env, "sendMessage", { chat_id: chatId, text: owner && String(owner) === String(chatId) ? OWNER_HELP : PUBLIC_HELP, reply_markup: owner && String(owner) === String(chatId) ? OWNER_KEYBOARD : PUBLIC_KEYBOARD });
        return;
      }
      if (cmd === "/claim") {
        if (owner && String(owner) !== String(chatId)) {
          await telegram(this.env, "sendMessage", { chat_id: chatId, text: "⛔ پنل مالک قبلاً ثبت شده است." });
          return;
        }
        await this.write("owner_chat_id", chatId);
        await this.write("owner_username", msg.from?.username || null);
        await this.write("claimed_at", new Date().toISOString());
        await this.event("owner_claimed", JSON.stringify({ chat_id: chatId }));
        await telegram(this.env, "sendMessage", { chat_id: chatId, text: `✅ پنل مالک ثبت شد.\n\n${OWNER_HELP}`, reply_markup: OWNER_KEYBOARD });
        return;
      }
      if (owner && String(owner) === String(chatId)) {
        if (cmd === "/help") await telegram(this.env, "sendMessage", { chat_id: chatId, text: OWNER_HELP, reply_markup: OWNER_KEYBOARD });
        else if (cmd === "/status" || cmd === "/report") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.buildReport() });
        else if (cmd === "/network") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.buildNetwork() });
        else if (cmd === "/logs") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.buildLogs() });
        else if (cmd === "/health") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.buildHealth() });
        else if (cmd === "/test") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.buildTest() });
        else if (cmd === "/run") {
          await this.write("force_run", { requested_at: new Date().toISOString(), requested_by: chatId });
          await this.event("manual_run_requested", JSON.stringify({ requested_by: chatId }));
          await telegram(this.env, "sendMessage", { chat_id: chatId, text: "✅ درخواست اجرای فوری ثبت شد. موتور انتشار در اولین چرخه GitHub آن را اجرا می‌کند." });
        } else await telegram(this.env, "sendMessage", { chat_id: chatId, text: "❓ فرمان ناشناخته است. /help را بزنید." });
      } else if (cmd === "/help") {
        await telegram(this.env, "sendMessage", { chat_id: chatId, text: PUBLIC_HELP, reply_markup: PUBLIC_KEYBOARD });
      }
      return;
    }

    if (["group", "supergroup"].includes(chat.type)) {
      await this.processGroupCommand(msg, cmd, args);
    }
  }

  async processGroupCommand(msg, cmd, args) {
    const chat = msg.chat;
    const chatId = Number(chat.id);
    if (cmd === "/help") {
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: PUBLIC_HELP, reply_markup: PUBLIC_KEYBOARD });
      return;
    }
    const userId = Number(msg.from?.id || 0);
    if (!userId) return;
    const member = await telegram(this.env, "getChatMember", { chat_id: chatId, user_id: userId });
    if (!["administrator", "creator"].includes(member.status)) {
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: "ℹ️ این فرمان فقط برای مدیران گروه قابل استفاده است." });
      return;
    }
    const all = await this.destinations();
    const key = String(chatId);
    if (!all[key]) all[key] = defaultDestination(chat, this.env.BOT_ID || null);
    const current = all[key];

    if (cmd === "/setup") {
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: `⚙️ تنظیمات این مقصد\n\nوضعیت: ${current.active ? "فعال ✅" : "متوقف ⏸"}\nپست روزانه: ${current.posts_per_day}\nزمان‌ها: ${(current.times || []).join(", ")}\n\nنمونه: /posts 2\nسپس: /times 10:00 20:00`, reply_markup: SETTINGS_KEYBOARD });
      return;
    }
    if (cmd === "/posts") {
      const n = Number(args[0]);
      if (!Number.isInteger(n) || n < 1 || n > 3) {
        await telegram(this.env, "sendMessage", { chat_id: chatId, text: "❌ تعداد پست باید بین ۱ تا ۳ باشد.\nمثال: /posts 2" });
        return;
      }
      current.posts_per_day = n;
      const defaults = ["10:00", "20:00", "22:00"];
      current.times = (current.times || []).slice(0, n);
      while (current.times.length < n) current.times.push(defaults[current.times.length]);
      current.admin_configured = true;
      current.updated_at = new Date().toISOString();
      all[key] = current;
      await this.write("destinations", all);
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: `✅ روزانه ${n} پست تنظیم شد.`, reply_markup: SETTINGS_KEYBOARD });
      return;
    }
    if (cmd === "/times") {
      const times = validTimes(args);
      if (times.length !== Number(current.posts_per_day || 1)) {
        await telegram(this.env, "sendMessage", { chat_id: chatId, text: `❌ برای ${current.posts_per_day} پست، دقیقاً ${current.posts_per_day} زمان معتبر لازم است.\nمثال: /times 10:00 20:00` });
        return;
      }
      current.times = times;
      current.admin_configured = true;
      current.updated_at = new Date().toISOString();
      all[key] = current;
      await this.write("destinations", all);
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: `✅ زمان‌های ارسال ثبت شد: ${times.join(", ")}`, reply_markup: SETTINGS_KEYBOARD });
      return;
    }
    if (cmd === "/on" || cmd === "/off") {
      current.active = cmd === "/on";
      current.admin_configured = true;
      current.updated_at = new Date().toISOString();
      all[key] = current;
      await this.write("destinations", all);
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: current.active ? "✅ ارسال محتوا فعال شد." : "⏸ ارسال محتوا متوقف شد.", reply_markup: SETTINGS_KEYBOARD });
      return;
    }
    await telegram(this.env, "sendMessage", { chat_id: chatId, text: "❓ فرمان ناشناخته است. /help را بزنید." });
  }

  async buildReport() {
    const all = await this.destinations();
    const active = Object.values(all).filter((x) => x.active);
    const groups = active.filter((x) => ["group", "supergroup"].includes(x.type)).length;
    const channels = active.filter((x) => x.type === "channel").length;
    return `📊 گزارش ContentSenderTelegram\n\n🤖 @Climavid_bot\n🌐 مقصدهای فعال: ${active.length}\n👥 گروه‌ها: ${groups}\n📣 کانال‌ها: ${channels}\n\nبرای جزئیات: /network\nبرای سلامت: /health\nبرای لاگ: /logs`;
  }

  async buildNetwork() {
    const all = await this.destinations();
    const active = Object.values(all).filter((x) => x.active);
    const lines = [`🌐 شبکه انتشار ClimaVids`, ``, `مقصدهای فعال: ${active.length}`, ``];
    active.sort((a, b) => String(a.title).localeCompare(String(b.title), "fa"));
    active.forEach((x, i) => {
      const kind = x.type === "channel" ? "کانال" : "گروه";
      const user = x.username ? ` | @${x.username}` : "";
      lines.push(`${i + 1}. ${x.title} — ${kind}${user} — ${x.posts_per_day} پست/روز — ${(x.times || []).join(", ")}`);
    });
    if (!active.length) lines.push("هنوز مقصد فعالی ثبت نشده است.");
    return lines.join("\n");
  }

  async buildLogs() {
    const rows = this.ctx.storage.sql.exec("SELECT at,kind,detail FROM events ORDER BY id DESC LIMIT 20").toArray();
    const lines = ["🧾 لاگ اخیر ContentSenderTelegram", ""];
    if (!rows.length) return lines.concat("هنوز رویدادی ثبت نشده است.").join("\n");
    for (const row of rows) lines.push(`• ${row.at} | ${row.kind} | ${row.detail}`);
    return lines.join("\n");
  }

  async buildHealth() {
    const me = await telegram(this.env, "getMe");
    const all = await this.destinations();
    const active = Object.values(all).filter((x) => x.active);
    let healthy = 0;
    const broken = [];
    for (const entry of active) {
      try {
        const member = await telegram(this.env, "getChatMember", { chat_id: Number(entry.chat_id), user_id: Number(me.id) });
        if (["administrator", "creator"].includes(member.status) && member.can_post_messages !== false) healthy += 1;
        else broken.push(`${entry.title}: ${member.status}`);
      } catch (error) { broken.push(`${entry.title}: ${error.message || error}`); }
    }
    return `🩺 سلامت ContentSenderTelegram\n\n✅ Bot API: @${me.username} | ID: ${me.id}\n✅ مقصدهای سالم: ${healthy}\n⚠️ نیازمند بررسی: ${broken.length}${broken.length ? `\n\n${broken.map((x) => `• ${x}`).join("\n")}` : ""}`;
  }

  async buildTest() {
    const me = await telegram(this.env, "getMe");
    const chat = await telegram(this.env, "getChat", { chat_id: "@climavids" });
    const member = await telegram(this.env, "getChatMember", { chat_id: "@climavids", user_id: Number(me.id) });
    return `🧪 تست اتصال\n\n✅ Bot: @${me.username}\n✅ مقصد: ${chat.title || "@climavids"}\n✅ وضعیت Bot: ${member.status}\n✅ امکان ارسال: ${member.can_post_messages !== false ? "بله" : "خیر"}\n\n📌 این تست هیچ محتوایی منتشر نمی‌کند.`;
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/health" && request.method === "GET") {
      return json({ ok: true, service: "ContentSenderTelegram Bot Interface" });
    }

    const id = env.BOT_STATE.idFromName("global");
    const stub = env.BOT_STATE.get(id);

    if (url.pathname === "/telegram/webhook" && request.method === "POST") {
      const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token") || "";
      const expected = env.WEBHOOK_SECRET || "";
      if (!expected || !(await timingSafeEqualText(secret, expected))) return text("unauthorized", 401);
      let update;
      try { update = await request.json(); } catch { return text("bad json", 400); }
      await stub.fetch("https://do/update", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ update }) });
      return new Response("ok");
    }

    if (url.pathname === "/internal/destinations" && request.method === "GET") {
      const authorization = request.headers.get("Authorization") || "";
      const expected = `Bearer ${(env.TELEGRAM_BOT_TOKEN || "").trim()}`;
      if (!expected || !(await timingSafeEqualText(authorization, expected))) return text("unauthorized", 401);
      const response = await stub.fetch("https://do/destinations");
      return response;
    }

    if (url.pathname === "/internal/force-run" && request.method === "POST") {
      const authorization = request.headers.get("Authorization") || "";
      const expected = `Bearer ${(env.TELEGRAM_BOT_TOKEN || "").trim()}`;
      if (!expected || !(await timingSafeEqualText(authorization, expected))) return text("unauthorized", 401);
      const response = await stub.fetch("https://do/force-run", { method: "POST" });
      return response;
    }

    return text("ContentSenderTelegram Bot Interface", 200);
  },
};

export async function handleDurableRequest(request, env, state) {
  const url = new URL(request.url);
  if (url.pathname === "/update" && request.method === "POST") {
    const payload = await request.json();
    env.BOT_STATE; // keep binding reachable through generated worker types
    await state.processUpdate(payload.update);
    return new Response("ok");
  }
  if (url.pathname === "/destinations") {
    const all = await state.destinations();
    return json(Object.values(all).filter((x) => x.active).map((x) => ({
      chat_id: x.chat_id,
      title: x.title,
      username: x.username,
      type: x.type,
      active: x.active,
      posts_per_day: x.posts_per_day,
      times: x.times,
      status: x.status,
    })));
  }
  if (url.pathname === "/force-run" && request.method === "POST") {
    const force = await state.read("force_run", null);
    if (!force) return json({ pending: false });
    await state.write("force_run", null);
    return json({ pending: true, requested_at: force.requested_at, requested_by: force.requested_by });
  }
  return text("not found", 404);
}

// Durable Object class must expose fetch to receive forwarded requests.
BotState.prototype.fetch = async function (request) {
  return handleDurableRequest(request, this.env, this);
};
