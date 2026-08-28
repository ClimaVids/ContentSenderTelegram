from pathlib import Path

p = Path('workers/bot-interface/src/index.js')
s = p.read_text(encoding='utf-8')

if 'const OWNER_KEYBOARD' not in s:
    marker = 'const TZ = "Asia/Tehran";\n'
    insert = '''const OWNER_KEYBOARD = { inline_keyboard: [\n  [{ text: "📊 وضعیت کلی", callback_data: "owner:status" }, { text: "📋 گزارش کامل", callback_data: "owner:report" }],\n  [{ text: "🌐 شبکه مقصدها", callback_data: "owner:network" }, { text: "🧾 لاگ‌ها", callback_data: "owner:logs" }],\n  [{ text: "🩺 سلامت", callback_data: "owner:health" }, { text: "🧪 تست", callback_data: "owner:test" }],\n  [{ text: "🚀 انتشار فوری", callback_data: "owner:run" }],\n] };\n\nconst PUBLIC_KEYBOARD = { inline_keyboard: [\n  [{ text: "⚙️ تنظیمات مقصد", callback_data: "dest:setup" }],\n  [{ text: "📝 تعداد پست روزانه", callback_data: "dest:posts" }, { text: "⏰ زمان‌بندی", callback_data: "dest:times" }],\n  [{ text: "▶️ فعال‌سازی", callback_data: "dest:on" }, { text: "⏸ توقف", callback_data: "dest:off" }],\n  [{ text: "❓ راهنما", callback_data: "dest:help" }],\n] };\n\nconst SETTINGS_KEYBOARD = PUBLIC_KEYBOARD;\n\n'''
    s = s.replace(marker, marker + insert, 1)

# Attach keyboards to the existing menu-producing replies.
s = s.replace('text: owner && String(owner) === String(chatId) ? OWNER_HELP : PUBLIC_HELP });', 'text: owner && String(owner) === String(chatId) ? OWNER_HELP : PUBLIC_HELP, reply_markup: owner && String(owner) === String(chatId) ? OWNER_KEYBOARD : PUBLIC_KEYBOARD });')
s = s.replace('text: `✅ پنل مالک ثبت شد.\\n\\n${OWNER_HELP}` });', 'text: `✅ پنل مالک ثبت شد.\\n\\n${OWNER_HELP}`, reply_markup: OWNER_KEYBOARD });')
s = s.replace('if (cmd === "/help") await telegram(this.env, "sendMessage", { chat_id: chatId, text: OWNER_HELP });', 'if (cmd === "/help") await telegram(this.env, "sendMessage", { chat_id: chatId, text: OWNER_HELP, reply_markup: OWNER_KEYBOARD });')
s = s.replace('await telegram(this.env, "sendMessage", { chat_id: chatId, text: PUBLIC_HELP });', 'await telegram(this.env, "sendMessage", { chat_id: chatId, text: PUBLIC_HELP, reply_markup: PUBLIC_KEYBOARD });')
s = s.replace('text: `⚙️ تنظیمات این مقصد\\n\\nوضعیت:', 'text: `⚙️ تنظیمات این مقصد\\n\\nوضعیت:')
s = s.replace('نمونه: /posts 2\\nسپس: /times 10:00 20:00` });', 'نمونه: /posts 2\\nسپس: /times 10:00 20:00`, reply_markup: SETTINGS_KEYBOARD });')
s = s.replace('text: `✅ روزانه ${n} پست تنظیم شد.` });', 'text: `✅ روزانه ${n} پست تنظیم شد.`, reply_markup: SETTINGS_KEYBOARD });')
s = s.replace('text: `✅ زمان‌های ارسال ثبت شد: ${times.join(", ")}` });', 'text: `✅ زمان‌های ارسال ثبت شد: ${times.join(", ")}`, reply_markup: SETTINGS_KEYBOARD });')
s = s.replace('text: current.active ? "✅ ارسال محتوا فعال شد." : "⏸ ارسال محتوا متوقف شد." });', 'text: current.active ? "✅ ارسال محتوا فعال شد." : "⏸ ارسال محتوا متوقف شد.", reply_markup: SETTINGS_KEYBOARD });')

# Add callback_query handling before the normal message parsing.
needle = '    if (!msg?.chat) return;\n    const [cmd, args] = command(msg.text);'
if 'const callback = update.callback_query || null;' not in s:
    callback_block = '''    const callback = update.callback_query || null;\n    if (callback) {\n      const callbackChat = callback.message?.chat;\n      const callbackId = Number(callback.from?.id || 0);\n      if (!callbackChat || callbackChat.type !== "private") {\n        try { await telegram(this.env, "answerCallbackQuery", { callback_query_id: callback.id, text: "این منو فقط در گفت‌وگوی خصوصی مالک یا مقصد قابل استفاده است." }); } catch {}\n        return;\n      }\n      const owner = await this.owner();\n      const isOwner = owner && String(owner) === String(callbackChat.id) && String(callbackId) === String(owner);\n      const data = String(callback.data || "");\n      try {\n        if (data.startsWith("owner:") && isOwner) {\n          const action = data.slice(6);\n          if (action === "status" || action === "report") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildReport(), reply_markup: OWNER_KEYBOARD });\n          else if (action === "network") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildNetwork(), reply_markup: OWNER_KEYBOARD });\n          else if (action === "logs") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildLogs(), reply_markup: OWNER_KEYBOARD });\n          else if (action === "health") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildHealth(), reply_markup: OWNER_KEYBOARD });\n          else if (action === "test") await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: await this.buildTest(), reply_markup: OWNER_KEYBOARD });\n          else if (action === "run") {\n            await this.write("force_run", { requested_at: new Date().toISOString(), requested_by: Number(owner) });\n            await this.event("manual_run_requested", JSON.stringify({ requested_by: Number(owner), via: "button" }));\n            await telegram(this.env, "sendMessage", { chat_id: Number(owner), text: "🚀 درخواست انتشار فوری ثبت شد. در اولین چرخه موتور انتشار اجرا می‌شود.", reply_markup: OWNER_KEYBOARD });\n          }\n        } else {\n          await telegram(this.env, "sendMessage", { chat_id: Number(callbackChat.id), text: PUBLIC_HELP, reply_markup: PUBLIC_KEYBOARD });\n        }\n        await telegram(this.env, "answerCallbackQuery", { callback_query_id: callback.id });\n      } catch (error) {\n        try { await telegram(this.env, "answerCallbackQuery", { callback_query_id: callback.id, text: "⚠️ خطا؛ دوباره تلاش کنید." }); } catch {}\n        await this.event("callback_error", String(error.message || error));\n      }\n      return;\n    }\n\n'''
    s = s.replace(needle, callback_block + needle, 1)

p.write_text(s, encoding='utf-8')

# Verify the expected edits happened.
for required in ['OWNER_KEYBOARD', 'PUBLIC_KEYBOARD', 'callback_query', 'reply_markup']:
    assert required in s, required
