import worker, { BotState as BaseBotState, handleDurableRequest } from "./index.js";

async function sha256Hex(value) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Production entrypoint. The original index.js contains the bot logic; this
// wrapper supplies the missing Durable Object fetch() dispatcher and derives
// the webhook secret from the existing Telegram token, so no fourth secret is
// required in GitHub/Cloudflare.
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
};
