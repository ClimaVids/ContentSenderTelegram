from pathlib import Path
import re

p = Path("workers/bot-interface/src/index.js")
s = p.read_text(encoding="utf-8")

start = s.index("const PUBLIC_HELP = `")
end = s.index("const JSON_HEADERS", start)
ui = r'''const PUBLIC_HELP = `🤖 ContentSenderTelegram | دستیار انتشار محتوای ClimaVids

محتوای منتخب آب، هواشناسی، اقلیم و محیط‌زیست را برای گروه‌ها و کانال‌هایی که ربات را فعال کرده‌اند منتشر می‌کنم.

🚀 مدیران: ربات را Administrator کنید و از دکمه‌های پایین برای تنظیم مقصد استفاده کنید.

📌 اطلاعات فنی و گزارش شبکه فقط برای مالک ربات قابل مشاهده است.`;

const OWNER_HELP = `🔐 پنل خصوصی مالک ContentSenderTelegram

از دکمه‌های پایین می‌توانید وضعیت، گزارش‌ها، سلامت سیستم و اجرای دستی انتشار را کنترل کنید.

فرمان‌های / نیز همچنان فعال هستند.`;

function keyboard(rows) {
  return { keyboard: rows.map(row => row.map(text => ({ text }))), resize_keyboard: true, is_persistent: true };
}

const OWNER_MAIN_KB = keyboard([
  ["⚙️ تنظیمات", "📤 انتشار محتوا"],
  ["📊 گزارش‌ها", "🩺 سلامت سیستم"],
  ["📖 راهنما"],
]);
const OWNER_SETTINGS_KB = keyboard([["📌 وضعیت ربات", "🔙 بازگشت"]]);
const OWNER_PUBLISH_KB = keyboard([
  ["🧪 تست بدون انتشار", "🚀 انتشار فوری"],
  ["📌 وضعیت آخرین انتشار", "🔙 بازگشت"],
]);
const OWNER_REPORT_KB = keyboard([
  ["📊 گزارش کلی", "🌐 مقصدها"],
  ["📋 لاگ‌ها", "🩺 سلامت سیستم"],
  ["🔙 بازگشت"],
]);
const ADMIN_KB = keyboard([["⚙️ تنظیمات", "📤 انتشار محتوا"], ["📖 راهنما"]]);
const ADMIN_SETTINGS_KB = keyboard([
  ["1️⃣ روزانه ۱ پست", "2️⃣ روزانه ۲ پست", "3️⃣ روزانه ۳ پست"],
  ["⏰ تنظیم زمان‌ها", "▶️ فعال‌سازی", "⏸ توقف"],
  ["📌 وضعیت تنظیمات", "🔙 بازگشت"],
]);
const ADMIN_PUBLISH_KB = keyboard([["🧪 تست تنظیمات", "🔙 بازگشت"]]);

function sendOptions(chat_id, textValue, reply_markup) {
  return telegram(this.env, "sendMessage", { chat_id, text: textValue, reply_markup });
}

'''
s = s[:start] + ui + s[end:]

marker = 'const [cmd, args] = command(msg.text);'
if marker not in s:
    raise SystemExit("command marker not found")
alias_block = r'''const aliases = {
      "📌 وضعیت ربات": "/status",
      "📤 انتشار محتوا": "__publish_menu__",
      "📊 گزارش‌ها": "__report_menu__",
      "🩺 سلامت سیستم": "/health",
      "📖 راهنما": "/help",
      "⚙️ تنظیمات": "__settings_menu__",
      "🧪 تست بدون انتشار": "/test",
      "🚀 انتشار فوری": "/run",
      "📌 وضعیت آخرین انتشار": "/report",
      "📊 گزارش کلی": "/report",
      "🌐 مقصدها": "/network",
      "📋 لاگ‌ها": "/logs",
      "🧪 تست تنظیمات": "/help",
      "1️⃣ روزانه ۱ پست": "/posts 1",
      "2️⃣ روزانه ۲ پست": "/posts 2",
      "3️⃣ روزانه ۳ پست": "/posts 3",
      "▶️ فعال‌سازی": "/on",
      "⏸ توقف": "/off",
      "🔙 بازگشت": "/start",
      "📌 وضعیت تنظیمات": "/setup",
      "⏰ تنظیم زمان‌ها": "/times",
    };
    const incomingText = String(msg.text || "").trim();
    if (["__publish_menu__", "__report_menu__", "__settings_menu__"].includes(aliases[incomingText])) {
      const target = aliases[incomingText];
      if (chat.type === "private" && target === "__publish_menu__") { await sendOptions(chatId, "📤 انتشار محتوا\n\nیک گزینه را انتخاب کنید:", OWNER_PUBLISH_KB); return; }
      if (chat.type === "private" && target === "__report_menu__") { await sendOptions(chatId, "📊 گزارش‌ها\n\nیک گزارش را انتخاب کنید:", OWNER_REPORT_KB); return; }
      if (target === "__settings_menu__") {
        await sendOptions(chatId, "⚙️ تنظیمات\n\nگزینه موردنظر را انتخاب کنید:", chat.type === "private" ? OWNER_SETTINGS_KB : ADMIN_SETTINGS_KB); return;
      }
    }
    const [cmd, args] = command(aliases[incomingText] || msg.text);'''
s = s.replace(marker, alias_block, 1)

s = s.replace(
'await telegram(this.env, "sendMessage", { chat_id: chatId, text: owner && String(owner) === String(chatId) ? OWNER_HELP : PUBLIC_HELP });',
'await sendOptions(chatId, owner && String(owner) === String(chatId) ? OWNER_HELP : PUBLIC_HELP, owner && String(owner) === String(chatId) ? OWNER_MAIN_KB : ADMIN_KB);'
)
s = s.replace(
'await telegram(this.env, "sendMessage", { chat_id: chatId, text: `✅ پنل مالک ثبت شد.\\n\\n${OWNER_HELP}` });',
'await sendOptions(chatId, `✅ پنل مالک ثبت شد.\\n\\n${OWNER_HELP}`, OWNER_MAIN_KB);'
)
s = s.replace(
'if (cmd === "/help") await telegram(this.env, "sendMessage", { chat_id: chatId, text: OWNER_HELP });',
'if (cmd === "/help") await sendOptions(chatId, OWNER_HELP, OWNER_MAIN_KB);'
)
s = s.replace(
'} else if (cmd === "/help") {\n        await telegram(this.env, "sendMessage", { chat_id: chatId, text: PUBLIC_HELP });',
'} else if (cmd === "/help") {\n        await sendOptions(chatId, PUBLIC_HELP, ADMIN_KB);'
)

# Group help and welcome keyboards.
s = s.replace(
'await telegram(this.env, "sendMessage", { chat_id: chatId, text: PUBLIC_HELP });\n      return;\n    }\n    const userId',
'await sendOptions(chatId, PUBLIC_HELP, ADMIN_KB);\n      return;\n    }\n    const userId', 1
)
s = s.replace(
'await telegram(this.env, "sendMessage", { chat_id: chat.id, text: `👋 سلام!\\n\\nربات انتشار محتوای ClimaVids فعال شد.\\n\\n${PUBLIC_HELP}` });',
'await sendOptions(chat.id, `👋 سلام!\\n\\nربات انتشار محتوای ClimaVids فعال شد.\\n\\n${PUBLIC_HELP}`, ADMIN_KB);'
)

# Make /setup return the settings keyboard in groups.
pattern = r'(if \(cmd === "/setup"\) \{\s*await telegram\(this\.env, "sendMessage", \{ chat_id: chatId, text: `⚙️ تنظیمات این مقصد[\s\S]*?` )\}\);'
m = re.search(pattern, s)
if m:
    old = m.group(0)
    if 'ADMIN_SETTINGS_KB' not in old:
        new = old[:-3] + ', reply_markup: ADMIN_SETTINGS_KB });'
        s = s.replace(old, new, 1)

# Do not leave a private settings button pointing to group-only /posts.
# It is intentionally just a status shortcut for the owner.

p.write_text(s, encoding="utf-8")
print("button UI patch applied")
