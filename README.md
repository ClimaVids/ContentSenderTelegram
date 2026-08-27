# ContentSenderTelegram

ربات و موتور توزیع محتوای فارسی **ClimaVids** برای کانال اصلی و گروه‌ها/کانال‌های همکار.

## معماری

- `@Climavid_bot` رابط تعاملی Telegram است.
- رابط Telegram روی **Cloudflare Workers + SQLite-backed Durable Object** اجرا می‌شود؛ بنابراین فرمان‌ها به GitHub Actions وابسته نیستند.
- GitHub Actions فقط موتور جمع‌آوری، پالایش، تولید و انتشار دوره‌ای محتوا را اجرا می‌کند.
- تنها Secret الزامی Telegram در GitHub: `TELEGRAM_BOT_TOKEN`.
- مقصد اصلی برند: `@climavids`.
- هر گروه یا کانالی که Bot را Administrator کند، از رویداد Telegram شناسایی و ثبت می‌شود.
- مقصد تازه‌ثبت‌شده به‌صورت پیش‌فرض **۱ پست در روز، ساعت ۲۰:۰۰ تهران** دریافت می‌کند.
- مدیر گروه می‌تواند تعداد پست را بین ۱ تا ۳ و زمان‌های همان مقصد را تنظیم کند.
- گزارش‌های شبکه، نام مقصدها و اطلاعات فنی فقط در پنل خصوصی مالک قابل مشاهده است.

## رابط Bot

### کاربران و مدیران گروه

- `/start` — شروع و راهنمای فارسی
- `/help` — راهنمای استفاده
- `/setup` — مشاهده تنظیمات همین مقصد
- `/posts 1` — یک پست در روز
- `/posts 2` — دو پست در روز
- `/posts 3` — سه پست در روز
- `/times 10:00` — تعیین ساعت برای یک پست
- `/times 10:00 20:00` — تعیین دو ساعت برای دو پست
- `/times 10:00 20:00 22:00` — تعیین سه ساعت برای سه پست
- `/on` — فعال‌سازی ارسال
- `/off` — توقف موقت ارسال

فقط مدیران همان گروه می‌توانند تنظیمات آن گروه را تغییر دهند.

### پنل خصوصی مالک

مالک در گفت‌وگوی خصوصی Bot یک بار `/claim` را ارسال می‌کند. سپس:

- `/status` — وضعیت کلی
- `/report` — گزارش کامل
- `/network` — تعداد و نام مقصدهای فعال
- `/logs` — لاگ رویدادها و خطاها
- `/health` — سلامت Bot و مقصدها
- `/test` — تست Bot و `@climavids` بدون انتشار
- `/run` — درخواست انتشار فوری

## منابع و تولید محتوا

- RSS و Telegram Web برای دریافت محتوای فارسی.
- **GDELT** برای دریافت سریع‌تر اخبار رسمی.
- **Gemini** به‌صورت اختیاری برای بازنویسی/خلاصه‌سازی؛ بدون کلید AI، موتور پایه فعال می‌ماند.

## کیفیت خروجی عمومی

پست‌های عمومی باید:

- بدون تیتر جداگانه باشند.
- بدون نام یا ID کانال منبع باشند.
- بدون لینک خبر منبع باشند.
- بدون Handle منبع باشند.
- بدون هشتگ‌های منبع باشند.
- در مرز جمله قطع نشوند.
- Footer کامل ClimaVids را حفظ کنند.

## Cloudflare Bot Interface

کد رابط در `workers/bot-interface/src/worker.js` است و وضعیت شبکه، مالک و لاگ‌ها را در SQLite-backed Durable Object نگهداری می‌کند.

Cloudflare برای Durable Objectهای جدید SQLite-backed storage را توصیه می‌کند. رابط Webhook نیز با `ctx.waitUntil()` پیام Telegram را سریع acknowledge می‌کند و پردازش را خارج از پاسخ اولیه ادامه می‌دهد.

برای استقرار، GitHub Actions از این موارد استفاده می‌کند:

- Secret: `TELEGRAM_BOT_TOKEN` — موجود
- Secret جدید: `CLOUDFLARE_ACCOUNT_ID`
- Secret جدید: `CLOUDFLARE_API_TOKEN`
- Repository Variable: `CLIMAVIDS_BOT_API_URL` — URL عمومی Worker

پس از Deploy، Workflow `Set ClimaVids Telegram Webhook` را یک بار اجرا کنید و URL Worker را وارد کنید. این Workflow Webhook را با Secret مشتق‌شده از Bot Token ثبت می‌کند.

وقتی `CLIMAVIDS_BOT_API_URL` تنظیم شود، Workflow قدیمی `owner-monitor.yml` خودکار متوقف می‌شود تا با Webhook تداخل نکند.

راهنمای کامل: `docs/CLOUDFLARE_BOT.md`

## Workflowهای اصلی

- `publish.yml` — توزیع محتوای مشترک در شبکه
- `deploy-worker.yml` — Deploy رابط Cloudflare
- `set-telegram-webhook.yml` — اتصال Telegram به Worker
- `owner-monitor.yml` — سازوکار Legacy؛ بعد از Cutover به Cloudflare no-op می‌شود
- `manual-publish.yml` — اجرای دستی موتور انتشار
- `live-smoke.yml` — تست اتصال Bot به کانال اصلی
- `collector-smoke.yml` — تست collectorها
- `ci.yml` — تست، compile و dry-run

## راه‌اندازی

### GitHub

همین Secret را نگه دارید:

`TELEGRAM_BOT_TOKEN`

دو Secret Cloudflare را اضافه کنید:

`CLOUDFLARE_ACCOUNT_ID`

`CLOUDFLARE_API_TOKEN`

و یک Repository Variable بسازید:

`CLIMAVIDS_BOT_API_URL`

که مقدار آن URL عمومی Worker خواهد بود.

### Telegram

`@Climavid_bot` باید در `@climavids` Administrator باشد.
برای استفاده در گروه، Bot را Administrator کنید. پس از دریافت `/setup` مدیر گروه می‌تواند تعداد و زمان‌های ارسال را تنظیم کند.
