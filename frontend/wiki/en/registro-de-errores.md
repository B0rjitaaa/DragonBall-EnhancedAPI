# Error log

When something fails, whether on the server, in a background task or in your browser, it gets recorded in the admin, under **Errors** (`/admin/errorlog/errorgroup/`). If the error is new, you also get a Telegram alert.

![The error log in the admin](../img/admin-errores.jpg)

## Where they come from

| Source | What it collects |
|---|---|
| **Server (API and admin)** | Any backend error: 500 failures in the API or the admin (with the method, the address and the browser) and errors logged by the code. |
| **Tasks (Celery)** | Errors in background tasks: syncs, prices, scanner… |
| **Web (browser)** | JavaScript errors in your browser while you use the web app, and API requests that fail (5xx) or are rejected (403), grouped by method, path and code. Only in the server version, not in development. |

In the browser:
- at most 10 different errors are sent per page;
- noise from browser extensions is ignored.

Sending is silent: you don't see anything on screen.

## Grouped by cause

Errors **aren't recorded one by one**: they're grouped by **type + place in the code**. If the same failure happens 200 times, you see a single row with:
- **times**: how many times it has happened;
- **first seen** and **last seen**;
- the latest **message**, **traceback**, **request** and **browser**.

The message doesn't count for grouping, because it usually changes with the data.

## The page

- **“status” filter:** **Pending** (the default), **Resolved** or **All**. You can also filter by source and by date.
- **Columns:** whether it's pending, the source, the type, the message (first line), the times, the last and the first time.
- **Actions:** select errors and apply one of these two:
  - **Mark as resolved**: when it's already fixed. If it happens again, **it reopens by itself**.
  - **Reopen**.
- **Read-only:** errors can't be created or edited by hand.

## Telegram alerts

An alert (silent, no sound) arrives in two cases:
- **🐞 New error**: a cause that hadn't been seen before;
- **🐞 A resolved error is back**: you marked it as resolved and it has happened again.

The alert includes the direct link to the error in the admin. If the same error repeats, **no more alerts arrive**: only its counter goes up.

## Cleanup

Every day at 05:30, errors **resolved more than 90 days ago** are deleted. Pending ones are never deleted automatically.
