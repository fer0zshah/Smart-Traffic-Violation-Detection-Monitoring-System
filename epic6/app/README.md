# Epic 6 — Database and Web Application

`ViolationDBWriter` reads MySQL settings from `app/.env`, upserts events by
their unique `event_id`, and copies full-frame and plate evidence into
Laravel's `storage/app/public/violations` directory.

Failed database writes are retried and then queued in
`epic6/app/pending_db_events.json`. A later run flushes queued records.

Connection and historical JSON import:

```powershell
python epic6\app\db_writer.py --ping
python epic6\app\db_writer.py --import-json violation_events.json
```

Create Laravel's public storage link once:

```powershell
cd epic6\app
php artisan storage:link
```
