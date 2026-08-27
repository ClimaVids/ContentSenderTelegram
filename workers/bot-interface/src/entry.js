import worker, { BotState as BaseBotState, handleDurableRequest } from "./index.js";

// Production entrypoint. The original index.js contains the bot logic; this
// wrapper gives the Durable Object an actual fetch() method so webhook requests
// are dispatched into BotState instead of stopping at an unhandled stub.fetch().
export class BotState extends BaseBotState {
  async fetch(request) {
    return handleDurableRequest(request, this.env, this);
  }
}

export default worker;
