# ContentSenderTelegram

ربات و موتور توزیع محتوای فارسی **ClimaVids**.

## معماری

- `@Climavid_bot` رابط Telegram است.
- رابط Bot روی Cloudflare Workers + SQLite-backed Durable Object اجرا می‌شود و به GitHub Actions برای پاسخ به فرمان‌ها وابسته نیست.
- GitHub Actions موتور جمع‌آوری، پالایش، تولید و انتشار دوره‌ای محتوا را اجرا می‌کند.
- Secretهای GitHub: `TELEGRAM_BOT_TOKEN`، `CLOUDFLARE_ACCOUNT_ID` و `CLOUDFLARE_API_TOKEN`.
- مقصد اصلی: `@climavids`.
- مقصد جدید با Administrator شدن Bot ثبت می‌شود.
- تنظیم پیش‌فرض مقصد: روزانه ۱ پست در ساعت ۲۰:۰۰ تهران.

## فرمان‌ها

### کاربران و مدیران

`/start` — شروع و راهنما

`/help` — راهنمای استفاده

`/setup` — تنظیمات مقصد

`/posts 1` / `/posts 2` / `/posts 3` — تعداد پست روزانه

`/times 10:00` یا `/times 10:00 20:00` — زمان‌های ارسال

`/on` / `/off` — فعال یا متوقف کردن ارسال

فقط مدیران همان مقصد می‌توانند تنظیمات آن را تغییر دهند.

### مالک

`/claim` — ثبت اولیه پنل مالک

`/status` — وضعیت کلی

`/report` — گزارش کامل

`/network` — مقصدهای فعال

`/logs` — لاگ‌ها و خطاها

`/health` — سلامت Bot و مقصدها

`/test` — تست بدون انتشار

`/run` — درخواست انتشار فوری

اطلاعات شبکه و گزارش‌های فنی فقط در گفت‌وگوی خصوصی مالک نمایش داده می‌شوند.

## کیفیت محتوای عمومی

پست‌ها بدون تیتر جداگانه، بدون لینک/نام/شناسه/هشتگ منبع و بدون جمله ناقص منتشر می‌شوند. Footer رسمی ClimaVids باید کامل حفظ شود.

## Cloudflare

Entrypoint فعال Wrangler: `workers/bot-interface/src/entry.js`

منطق Bot و Durable Object: `workers/bot-interface/src/index.js`

URL Worker: `https://climavids-content-sender-bot.birjand-climate.workers.dev`

Webhook: `https://climavids-content-sender-bot.birjand-climate.workers.dev/telegram/webhook`

CI روی Push به `main` تست‌ها، اعتبارسنجی Worker، Deploy Cloudflare، ثبت Secret Telegram و تنظیم Webhook را انجام می‌دهد.

## Workflowهای اصلی

- `ci.yml` — تست، compile، dry-run، Deploy Worker و Webhook
- `publish.yml` — انتشار محتوای شبکه
- `manual-publish.yml` — اجرای دستی انتشار
- `live-smoke.yml` — تست زنده
- `collector-smoke.yml` — تست collectorها
- `alert.yml` — هشدار خطاها

## راه‌اندازی

فقط این سه Repository Secret لازم است:

`TELEGRAM_BOT_TOKEN`

`CLOUDFLARE_ACCOUNT_ID`

`CLOUDFLARE_API_TOKEN`

نیازی به `TELEGRAM_CHAT_ID` یا `TELEGRAM_OWNER_CHAT_ID` نیست؛ مالک با `/claim` ثبت می‌شود.

`@Climavid_bot` برای انتشار در `@climavids` و مقصدهای دیگر باید Administrator باشد.

## ⭐ Support, Sponsorship & Collaboration

اگر این پروژه برای شما مفید است، حمایت شما به توسعه و نگهداری ابزارهای متن‌باز **ClimaVids** کمک می‌کند.

### حمایت از پروژه

راهنمای کامل حمایت مالی و غیرمالی در [SUPPORT.md](SUPPORT.md) قرار دارد.

- ⭐ یک Star به پروژه بدهید.
- 🐛 باگ‌ها را گزارش کنید.
- 💡 قابلیت‌های جدید پیشنهاد دهید.
- 🔧 در توسعه با Pull Request مشارکت کنید.

### همکاری تجاری

برای توسعه سفارشی Telegram Bot، اتوماسیون محتوا، Cloudflare Workers، Python و ابزارهای اقلیمی می‌توان درباره پروژه همکاری کرد.

جزئیات خدمات در [SERVICES.md](SERVICES.md) آمده است.

📧 `birjand.climate@yahoo.com`

### Funding

در صورت فعال‌شدن یک روش رسمی و قابل‌دریافت برای حمایت مالی، لینک آن در تنظیمات Funding ریپازیتوری اضافه خواهد شد. هیچ آدرس پرداخت جعلی یا غیرقابل‌تأییدی در پروژه قرار نمی‌گیرد.

---

**ClimaVids** — Open-source tools for climate, weather and content automation.
