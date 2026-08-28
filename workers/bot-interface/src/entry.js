import worker, { BotState as BaseBotState, handleDurableRequest } from "./index.js";

async function sha256Hex(value) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function configureWebhook(env) {
  const token = String(env.TELEGRAM_BOT_TOKEN || "").trim();
  if (!token) return;
  const secret = await sha256Hex(token);
  const workerUrl = "https://climavids-content-sender-bot.birjand-climate.workers.dev";
  const response = await fetch(`https://api.telegram.org/bot${token}/setWebhook`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      url: `${workerUrl}/telegram/webhook`,
      secret_token: secret,
      drop_pending_updates: false,
      allowed_updates: ["message", "my_chat_member", "channel_post", "callback_query"],
    }),
  });
  if (!response.ok) throw new Error(`Telegram webhook setup failed: ${response.status}`);
}

export class BotState extends BaseBotState {
  async fetch(request) {
    return handleDurableRequest(request, this.env, this);
  }
}

export default {
  async fetch(request, env, ctx) {
    const token = String(env.TELEGRAM_BOT_TOKEN || "").trim();
    const effectiveEnv = token
      ? { ...env, WEBHOOK_SECRET: await sha256Hex(token) }
      : env;
    return worker.fetch(request, effectiveEnv, ctx);
  },

  async scheduled(_event, env, ctx) {
    ctx.waitUntil(configureWebhook(env).catch(() => undefined));
  },
};
