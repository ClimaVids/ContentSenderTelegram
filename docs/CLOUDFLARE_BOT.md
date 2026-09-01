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

## تنظیمات موردنیاز GitHub

در Repository `ClimaVids/ContentSenderTelegram` این Secrets را اضافه کنید:

1. `TELEGRAM_BOT_TOKEN`
2. `CLOUDFLARE_ACCOUNT_ID`
3. `CLOUDFLARE_API_TOKEN`

برای مالک Telegram نیازی به Secret جداگانه نیست؛ مالک با `/claim` ثبت می‌شود.

`CLIMAVIDS_BOT_API_URL` یک URL عمومی و غیرمحرمانه است. Publisher در حال حاضر URL رسمی Worker را به‌عنوان fallback داخلی نیز می‌شناسد تا نبودن Repository Variable باعث قطع ارتباط نشود.

## Deploy

Workflow `bot-deploy.yml` رابط Worker را Deploy می‌کند، Secret ربات را به Worker می‌دهد و Webhook تلگرام را با این رویدادها تنظیم می‌کند:

- `message`
- `my_chat_member`
- `channel_post`
- `callback_query`

در هر Deploy، تنظیم Webhook نیز Verify می‌شود.

## معماری دریافت Update

**Webhook تنها مسیر دریافت Updateهای Bot است.**

Workflow قدیمی Polling (`owner-monitor.yml`) حذف شده است و نباید هیچ Workflow دیگری `getUpdates` یا `deleteWebhook` را برای این Bot اجرا کند. وجود هم‌زمان Polling و Webhook می‌تواند باعث خطای Telegram `409 Conflict` شود.

## انتشار

Workflow `publish.yml` هر ۵ دقیقه اجرا می‌شود و:

1. Token را بررسی می‌کند.
2. اتصال به Bot Interface و فهرست مقصدها را Verify می‌کند.
3. `publish-network` را اجرا می‌کند.
4. درخواست `force_run` ثبت‌شده توسط `/run` را مصرف می‌کند.
5. state و خطاها را ثبت می‌کند.

## تست مالک

در چت خصوصی Bot:

1. `/claim`
2. `/status`
3. `/health`
4. `/test`
5. دکمه `🚀 انتشار فوری`
6. مشاهده `🧾 لاگ‌ها`

## نکته درباره مقصدها

`my_chat_member` برای ثبت خودکار گروه‌ها و کانال‌هایی که Bot در آنها Administrator می‌شود استفاده می‌شود.

مدیران گروه می‌توانند تنظیمات مقصد خود را با پنل دکمه‌ای یا فرمان‌های متنی تغییر دهند.
