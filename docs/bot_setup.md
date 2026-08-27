# راه‌اندازی @Climavid_bot

## Secret

تنها Secret لازم در GitHub Actions:

`TELEGRAM_BOT_TOKEN`

مقدار آن باید Token رسمی `@Climavid_bot` باشد.

## مقصد

موتور انتشار مقصد را داخل کد روی `@climavids` تنظیم کرده است. نیازی به `TELEGRAM_CHAT_ID` نیست.

## مالک

در گفت‌وگوی خصوصی با Bot، مالک برای اولین بار `/claim` را می‌فرستد. سیستم شناسه همان چت خصوصی را در `data/owner_state.json` ذخیره می‌کند. بعد از آن فقط همان چت خصوصی پنل مدیریتی را دریافت می‌کند.

## دستورات مالک

`/claim`

`/help`

`/status`

`/report`

`/logs`

`/test`
