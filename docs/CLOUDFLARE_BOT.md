# انتقال رابط Telegram به Cloudflare Workers

هدف این لایه آن است که `@Climavid_bot` برای فرمان‌ها و مدیریت مقصدها به‌صورت webhook روی Cloudflare Workers در دسترس باشد و GitHub Actions فقط موتور تولید/انتشار محتوا را اجرا کند.

## ساختار

```text
Telegram
  │
  ▼
Cloudflare Worker + Durable Object (SQLite)
  │
  ├─ فرمان‌های مالک و مدیران
  ├─ ثبت گروه/کانال هنگام Administrator شدن Bot
  ├─ تنظیم /posts و /times و /on و /off
  └─ نگهداری گزارش و لاگ
          │
          ▼
GitHub Actions
  │
  ├─ جمع‌آوری RSS / GDELT / Telegram Web
  ├─ پالایش و تولید متن
  └─ انتشار به مقصدهای فعال
```

Cloudflare توصیه می‌کند برای Durable Objectهای جدید از SQLite-backed storage استفاده شود. رابط Worker نیز از `ctx.waitUntil()` برای پردازش پس از پاسخ Webhook استفاده می‌کند تا Telegram سریع پاسخ HTTP دریافت کند.

## تنظیمات موردنیاز GitHub

در Repository `ClimaVids/ContentSenderTelegram` این Secrets را اضافه کنید:

1. `TELEGRAM_BOT_TOKEN` — از قبل موجود است.
2. `CLOUDFLARE_ACCOUNT_ID` — شناسه Account در Cloudflare.
3. `CLOUDFLARE_API_TOKEN` — API Token با دسترسی لازم برای Workers Scripts/Deploy.

هیچ Secret دیگری برای مالک Telegram لازم نیست.

یک Repository Variable نیز اضافه کنید:

`CLIMAVIDS_BOT_API_URL`

مقدار آن URL عمومی Worker است، مثلاً:

`https://climavids-content-sender-bot.<subdomain>.workers.dev`

این URL محرمانه نیست و به‌صورت Variable نگهداری می‌شود، نه Secret.

## Deploy

Workflow زیر با هر تغییر در `workers/bot-interface/` قابل اجرا است:

`Deploy ClimaVids Telegram Bot Interface`

این Workflow:

- JavaScript Worker را syntax-check می‌کند.
- Worker و Durable Object را deploy می‌کند.
- `TELEGRAM_BOT_TOKEN` را به Worker می‌دهد.
- Secret مربوط به Webhook را به‌صورت SHA-256 از همان Bot Token تولید و ذخیره می‌کند.

## فعال‌کردن Webhook

پس از موفقیت Deploy، URL Worker را بردارید.

سپس Workflow زیر را از Actions اجرا کنید:

`Set ClimaVids Telegram Webhook`

در ورودی `worker_url` فقط URL اصلی Worker را وارد کنید؛ Workflow خودش `/telegram/webhook` را اضافه و Webhook را ثبت می‌کند.

## قطع Polling قدیمی

وقتی `CLIMAVIDS_BOT_API_URL` در Repository Variables قرار گرفت، Workflow قدیمی `owner-monitor.yml` خودکار به حالت no-op می‌رود. این موضوع مهم است، چون بعد از Webhook نباید Workflow قدیمی دوباره `deleteWebhook` یا `getUpdates` را اجرا کند.

## تست

بعد از Webhook:

1. در چت خصوصی Bot، `/claim`
2. سپس `/status`
3. سپس `/test`
4. برای تست انتشار: `/run`

در گروه نیز Bot را Administrator کنید و `/setup` را اجرا کنید.

## نکته درباره کانال‌ها

رویداد `my_chat_member` برای ثبت کانال هنگام Administrator شدن Bot پشتیبانی می‌شود. فرمان‌های تعاملی مدیران در این نسخه برای group/supergroup طراحی شده‌اند؛ مدیریت تنظیمات کانال از پنل مالک/رابط مدیریتی قابل توسعه است.
