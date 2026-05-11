# Backup automático de la DB de RCA. (versión PowerShell para Windows)
#
# Uso:
#   $env:BACKUP_DIR = "C:\backups\rca"
#   $env:RETENTION_DAYS = "30"
#   .\scripts\backup_db.ps1

$ErrorActionPreference = "Stop"

$BackupDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { ".\backups" }
$Retention = if ($env:RETENTION_DAYS) { [int]$env:RETENTION_DAYS } else { 30 }
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Cargar .env si DATABASE_URL no está en env
if (-not $env:DATABASE_URL -and (Test-Path .env)) {
    Get-Content .env | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | ForEach-Object {
        $kv = $_ -split '=', 2
        Set-Item -Path "env:$($kv[0].Trim())" -Value $kv[1].Trim()
    }
}

if (-not $env:DATABASE_URL) {
    Write-Error "[backup] DATABASE_URL no está seteada"
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$dbUrl = $env:DATABASE_URL

if ($dbUrl.StartsWith("sqlite")) {
    $dbFile = $dbUrl -replace '^sqlite:///', ''
    if (-not (Test-Path $dbFile)) {
        Write-Error "[backup] archivo SQLite no existe: $dbFile"
    }
    $out = Join-Path $BackupDir "rca_$Timestamp.sqlite"
    Write-Host "[backup] SQLite -> $out"
    # `.backup` consistente
    & sqlite3 $dbFile ".backup '$out'"
    Compress-Archive -Path $out -DestinationPath "$out.zip"
    Remove-Item $out
    Write-Host "[backup] OK $out.zip"
} elseif ($dbUrl.StartsWith("postgres")) {
    $out = Join-Path $BackupDir "rca_$Timestamp.dump"
    Write-Host "[backup] Postgres -> $out"
    & pg_dump --format=custom --compress=9 --no-owner --no-privileges --dbname=$dbUrl --file=$out
    Write-Host "[backup] OK $out"
} else {
    Write-Error "[backup] tipo de DB no soportado: $dbUrl"
}

# Retención
Write-Host "[backup] Limpiando backups con más de $Retention días..."
Get-ChildItem -Path $BackupDir -Filter "rca_*" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$Retention) } |
    Remove-Item -Verbose

Write-Host "[backup] done"
