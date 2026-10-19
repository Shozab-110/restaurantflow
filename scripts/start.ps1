$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if ((Test-Path -LiteralPath '.local\pgsql\bin\pg_ctl.exe') -or (Test-Path -LiteralPath '.local\pg-runtime\pgsql\bin\pg_ctl.exe')) {
    & '.\.venv\Scripts\python.exe' 'scripts\local_postgres.py' start
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed.' }
}
& '.\.venv\Scripts\python.exe' 'manage.py' runserver 127.0.0.1:8000 --noreload
