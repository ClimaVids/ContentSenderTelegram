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

🔒 آمار شبکه و اطلاعات فنی فقط برای مالک ربات قابل مشاهده است.`;

const OWNER_HELP = `🔐 پنل خصوصی مالک ContentSenderTelegram

/status — وضعیت کلی
/report — گزارش کامل
/network — تعداد و نام مقصدها
/logs — لاگ رویدادها و خطاها
/health — سلامت Bot و مقصدها
/test — تست Bot و کانال اصلی
/run — درخواست اجرای فوری انتشار

/claim — ثبت این گفت‌وگوی خصوصی به عنوان مالک`;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json; charset=utf-8" } });
}

function text(body, status = 200) {
  return new Response(body, { status, headers: { "content-type": "text/plain; charset=utf-8" } });
}

async function digestText(value) {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
}

async function safeEqual(a, b) {
  const [left, right] = await Promise.all([digestText(a), digestText(b)]);
  return crypto.subtle.timingSafeEqual(left, right);
}

async function telegram(env, method, payload = {}) {
  const token = String(env.TELEGRAM_BOT_TOKEN || "").trim();
  if (!token) throw new Error("TELEGRAM_BOT_TOKEN تنظیم نشده است.");
  const response = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.description || `Telegram ${method} failed`);
  return data.result;
}

function parseCommand(value) {
  const parts = String(value || "").trim().split(/\s+/);
  if (!parts[0] || !parts[0].startsWith("/")) return { command: null, args: [] };
  return { command: parts[0].split("@", 1)[0].toLowerCase(), args: parts.slice(1) };
}

function normaliseTimes(args) {
  const result = [];
  for (const value of args) {
    const match = /^(\d{1,2}):(\d{2})$/.exec(value);
    if (!match) continue;
    const h = Number(match[1]);
    const m = Number(match[2]);
    if (h >= 0 && h <= 23 && m >= 0 && m <= 59) result.push(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
  }
  return [...new Set(result)].sort();
}

function newDestination(chat, botId) {
  return {
    chat_id: Number(chat.id),
    title: chat.title || chat.username || String(chat.id),
    username: chat.username || null,
    type: chat.type,
    status: "administrator",
    active: true,
    posts_per_day: 1,
    times: ["20:00"],
    bot_id: botId || null,
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

  async get(key, fallback = null) {
    const row = this.ctx.storage.sql.exec("SELECT value FROM kv WHERE key = ?", key).toArray()[0];
    if (!row) return fallback;
    try { return JSON.parse(row.value); } catch { return row.value; }
  }

  async put(key, value) {
    this.ctx.storage.sql.exec("INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", key, JSON.stringify(value));
  }

  async addEvent(kind, detail) {
    this.ctx.storage.sql.exec("INSERT INTO events(at,kind,detail) VALUES(?,?,?)", new Date().toISOString(), kind, detail);
    this.ctx.storage.sql.exec("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 200)");
  }

  async destinations() {
    return (await this.get("destinations", {})) || {};
  }

  async ownerId() {
    return await this.get("owner_chat_id", null);
  }

  async ensurePrimary() {
    try {
      const me = await telegram(this.env, "getMe");
      const chat = await telegram(this.env, "getChat", { chat_id: "@climavids" });
      const member = await telegram(this.env, "getChatMember", { chat_id: "@climavids", user_id: Number(me.id) });
      if (!["administrator", "creator"].includes(member.status)) return;
      const all = await this.destinations();
      const key = String(chat.id);
      const old = all[key] || newDestination(chat, me.id);
      old.title = chat.title || "ClimaVids";
      old.username = chat.username || "climavids";
      old.type = chat.type;
      old.status = member.status;
      old.active = true;
      old.is_primary = true;
      all[key] = old;
      await this.put("destinations", all);
    } catch (error) {
      await this.addEvent("primary_health_error", String(error.message || error));
    }
  }

  async handleUpdate(update) {
    const membership = update.my_chat_member;
    if (membership) {
      const chat = membership.chat || {};
      const status = membership.new_chat_member?.status || "unknown";
      if (!["group", "supergroup", "channel"].includes(chat.type)) return;
      const all = await this.destinations();
      const key = String(chat.id);
      const old = all[key] || newDestination(chat, update.my_chat_member?.new_chat_member?.user?.id);
      old.title = chat.title || chat.username || old.title;
      old.username = chat.username || old.username || null;
      old.type = chat.type;
      old.status = status;
      old.active = ["administrator", "creator"].includes(status);
      old.updated_at = new Date().toISOString();
      if (old.active) {
        all[key] = old;
        await this.put("destinations", all);
        await this.addEvent("destination_added", JSON.stringify({ id: chat.id, title: old.title, type: chat.type }));
        if (chat.type !== "channel" && !old.welcome_sent) {
          try {
            await telegram(this.env, "sendMessage", { chat_id: chat.id, text: `👋 سلام!\n\nربات انتشار محتوای ClimaVids فعال شد.\n\n${PUBLIC_HELP}` });
            old.welcome_sent = true;
            all[key] = old;
            await this.put("destinations", all);
          } catch (error) {
            await this.addEvent("welcome_error", String(error.message || error));
          }
        }
      } else if (["left", "kicked"].includes(status) && all[key]) {
        all[key].active = false;
        await this.put("destinations", all);
        await this.addEvent("destination_removed", JSON.stringify({ id: chat.id, status }));
      }
      return;
    }

    const msg = update.message || update.channel_post;
    if (!msg?.chat) return;
    const { command, args } = parseCommand(msg.text);
    if (!command) return;
    const chat = msg.chat;
    const chatId = Number(chat.id);

    if (chat.type === "private") {
      const owner = await this.ownerId();
      if (command === "/start") {
        await telegram(this.env, "sendMessage", { chat_id: chatId, text: owner && String(owner) === String(chatId) ? OWNER_HELP : PUBLIC_HELP });
        return;
      }
      if (command === "/claim") {
        if (owner && String(owner) !== String(chatId)) {
          await telegram(this.env, "sendMessage", { chat_id: chatId, text: "⛔ پنل مالک قبلاً ثبت شده است." });
          return;
        }
        await this.put("owner_chat_id", chatId);
        await this.put("owner_username", msg.from?.username || null);
        await this.put("claimed_at", new Date().toISOString());
        await this.addEvent("owner_claimed", JSON.stringify({ chat_id: chatId }));
        await telegram(this.env, "sendMessage", { chat_id: chatId, text: `✅ پنل مالک ثبت شد.\n\n${OWNER_HELP}` });
        return;
      }
      if (owner && String(owner) === String(chatId)) {
        if (command === "/help") await telegram(this.env, "sendMessage", { chat_id: chatId, text: OWNER_HELP });
        else if (command === "/status" || command === "/report") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.report() });
        else if (command === "/network") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.networkReport() });
        else if (command === "/logs") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.logs() });
        else if (command === "/health") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.health() });
        else if (command === "/test") await telegram(this.env, "sendMessage", { chat_id: chatId, text: await this.test() });
        else if (command === "/run") {
          await this.put("force_run", { requested_at: new Date().toISOString(), requested_by: chatId });
          await this.addEvent("manual_run_requested", JSON.stringify({ chat_id: chatId }));
          await telegram(this.env, "sendMessage", { chat_id: chatId, text: "✅ درخواست اجرای فوری ثبت شد. موتور انتشار آن را در اولین چرخه پردازش می‌کند." });
        } else await telegram(this.env, "sendMessage", { chat_id: chatId, text: "❓ فرمان ناشناخته است. /help را بزنید." });
      } else if (command === "/help") {
        await telegram(this.env, "sendMessage", { chat_id: chatId, text: PUBLIC_HELP });
      }
      return;
    }

    if (["group", "supergroup"].includes(chat.type)) await this.groupCommand(msg, command, args);
  }

  async groupCommand(msg, command, args) {
    const chatId = Number(msg.chat.id);
    if (command === "/help") {
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: PUBLIC_HELP });
      return;
    }
    const userId = Number(msg.from?.id || 0);
    if (!userId) return;
    const member = await telegram(this.env, "getChatMember", { chat_id: chatId, user_id: userId });
    if (!["administrator", "creator"].includes(member.status)) {
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: "ℹ️ این فرمان فقط برای مدیران همین گروه قابل استفاده است." });
      return;
    }
    const all = await this.destinations();
    const key = String(chatId);
    if (!all[key]) all[key] = newDestination(msg.chat, null);
    const current = all[key];

    if (command === "/setup") {
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: `⚙️ تنظیمات این مقصد\n\nوضعیت: ${current.active ? "فعال ✅" : "متوقف ⏸"}\nتعداد پست: ${current.posts_per_day}\nزمان‌ها: ${(current.times || []).join(", ")}\n\nبرای تغییر تعداد: /posts 2\nبرای تغییر زمان: /times 10:00 20:00` });
      return;
    }
    if (command === "/posts") {
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
      await this.put("destinations", all);
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: `✅ تعداد ${n} پست در روز تنظیم شد.` });
      return;
    }
    if (command === "/times") {
      const times = normaliseTimes(args);
      const count = Number(current.posts_per_day || 1);
      if (times.length !== count) {
        await telegram(this.env, "sendMessage", { chat_id: chatId, text: `❌ برای ${count} پست، دقیقاً ${count} زمان معتبر لازم است.\nمثال: /times 10:00 20:00` });
        return;
      }
      current.times = times;
      current.admin_configured = true;
      current.updated_at = new Date().toISOString();
      all[key] = current;
      await this.put("destinations", all);
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: `✅ زمان‌های ارسال ثبت شد: ${times.join(", ")}` });
      return;
    }
    if (command === "/on" || command === "/off") {
      current.active = command === "/on";
      current.admin_configured = true;
      current.updated_at = new Date().toISOString();
      all[key] = current;
      await this.put("destinations", all);
      await telegram(this.env, "sendMessage", { chat_id: chatId, text: current.active ? "✅ ارسال محتوا فعال شد." : "⏸ ارسال محتوا متوقف شد." });
      return;
    }
    await telegram(this.env, "sendMessage", { chat_id: chatId, text: "❓ فرمان ناشناخته است. /help را بزنید." });
  }

  async report() {
    const all = await this.destinations();
    const active = Object.values(all).filter((x) => x.active);
    const groups = active.filter((x) => ["group", "supergroup"].includes(x.type)).length;
    const channels = active.filter((x) => x.type === "channel").length;
    return `📊 گزارش ContentSenderTelegram\n\n🤖 @Climavid_bot\n🌐 مقصدهای فعال: ${active.length}\n👥 گروه‌ها: ${groups}\n📣 کانال‌ها: ${channels}\n\n/network برای فهرست مقصدها\n/health برای سلامت\n/logs برای جزئیات فنی`;
  }

  async networkReport() {
    const all = await this.destinations();
    const active = Object.values(all).filter((x) => x.active);
    active.sort((a, b) => String(a.title).localeCompare(String(b.title), "fa"));
    const lines = ["🌐 شبکه انتشار ClimaVids", "", `مقصدهای فعال: ${active.length}`, ""];
    active.forEach((x, i) => {
      const kind = x.type === "channel" ? "کانال" : "گروه";
      const user = x.username ? ` | @${x.username}` : "";
      lines.push(`${i + 1}. ${x.title} — ${kind}${user} — ${x.posts_per_day} پست/روز — ${(x.times || []).join(", ")}`);
    });
    if (!active.length) lines.push("هنوز هیچ مقصد فعالی ثبت نشده است.");
    return lines.join("\n");
  }

  async logs() {
    const rows = this.ctx.storage.sql.exec("SELECT at,kind,detail FROM events ORDER BY id DESC LIMIT 25").toArray();
    if (!rows.length) return "🧾 لاگ ContentSenderTelegram\n\nهنوز رویدادی ثبت نشده است.";
    return ["🧾 لاگ اخیر ContentSenderTelegram", "", ...rows.map((r) => `• ${r.at} | ${r.kind} | ${r.detail}`)].join("\n");
  }

  async health() {
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

  async test() {
    const me = await telegram(this.env, "getMe");
    const chat = await telegram(this.env, "getChat", { chat_id: "@climavids" });
    const member = await telegram(this.env, "getChatMember", { chat_id: "@climavids", user_id: Number(me.id) });
    return `🧪 تست اتصال\n\n✅ Bot: @${me.username}\n✅ مقصد: ${chat.title || "@climavids"}\n✅ وضعیت Bot: ${member.status}\n✅ امکان ارسال: ${member.can_post_messages !== false ? "بله" : "خیر"}\n\n📌 این تست هیچ محتوایی منتشر نمی‌کند.`;
  }

  async takeForceRun() {
    const pending = await this.get("force_run", null);
    if (!pending) return json({ pending: false });
    await this.put("force_run", null);
    return json({ pending: true, requested_at: pending.requested_at, requested_by: pending.requested_by });
  }

  async scheduledReports() {
    const owner = await this.ownerId();
    if (!owner) return;
    const now = new Date();
    const iran = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tehran", hour: "2-digit", minute: "2-digit", hour12: false }).format(now);
    const [hour] = iran.split(":").map(Number);
    const type = hour === 9 ? "morning" : hour === 21 ? "night" : null;
    if (!type) return;
    const date = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tehran" }).format(now);
    const key = `${date}|${type}`;
    const sent = await this.get("scheduled_reports", {});
    if (sent[key]) return;
    await this.put("scheduled_reports", { ...sent, [key]: true });
    await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: `${type === "morning" ? "☀️ گزارش صبحگاهی" : "🌙 گزارش شبانه"}\n\n${await this.report()}` });
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/update" && request.method === "POST") {
      const data = await request.json();
      await this.handleUpdate(data.update);
      return text("ok");
    }
    if (url.pathname === "/destinations" && request.method === "GET") {
      await this.ensurePrimary();
      const all = await this.destinations();
      return json(Object.values(all).filter((x) => x.active).map((x) => ({ chat_id: x.chat_id, title: x.title, username: x.username, type: x.type, active: x.active, posts_per_day: x.posts_per_day, times: x.times, status: x.status })));
    }
    if (url.pathname === "/force-run" && request.method === "POST") return await this.takeForceRun();
    if (url.pathname === "/scheduled-reports" && request.method === "POST") {
      await this.scheduledReports();
      return text("ok");
    }
    return text("not found", 404);
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/health" && request.method === "GET") return json({ ok: true, service: "ContentSenderTelegram Bot Interface" });

    const id = env.BOT_STATE.idFromName("global");
    const state = env.BOT_STATE.get(id);

    if (url.pathname === "/telegram/webhook" && request.method === "POST") {
      const provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token") || "";
      const expected = String(env.WEBHOOK_SECRET || "");
      if (!expected || !(await safeEqual(provided, expected))) return text("unauthorized", 401);
      let payload;
      try { payload = await request.json(); } catch { return text("bad json", 400); }
      ctx.waitUntil(state.fetch("https://do/update", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) }));
      return text("ok");
    }

    if (url.pathname === "/internal/destinations" && request.method === "GET") {
      const provided = request.headers.get("Authorization") || "";
      const expected = `Bearer ${String(env.TELEGRAM_BOT_TOKEN || "").trim()}`;
      if (!expected || !(await safeEqual(provided, expected))) return text("unauthorized", 401);
      return await state.fetch("https://do/destinations");
    }

    if (url.pathname === "/internal/force-run" && request.method === "POST") {
      const provided = request.headers.get("Authorization") || "";
      const expected = `Bearer ${String(env.TELEGRAM_BOT_TOKEN || "").trim()}`;
      if (!expected || !(await safeEqual(provided, expected))) return text("unauthorized", 401);
      return await state.fetch("https://do/force-run", { method: "POST" });
    }

    if (url.pathname === "/internal/scheduled-reports" && request.method === "POST") {
      const provided = request.headers.get("Authorization") || "";
      const expected = `Bearer ${String(env.TELEGRAM_BOT_TOKEN || "").trim()}`;
      if (!expected || !(await safeEqual(provided, expected))) return text("unauthorized", 401);
      return await state.fetch("https://do/scheduled-reports", { method: "POST" });
    }

    return text("ContentSenderTelegram Bot Interface", 200);
  },

  async scheduled(_controller, env, ctx) {
    const id = env.BOT_STATE.idFromName("global");
    ctx.waitUntil(env.BOT_STATE.get(id).fetch("https://do/scheduled-reports", { method: "POST" }));
  },
};
