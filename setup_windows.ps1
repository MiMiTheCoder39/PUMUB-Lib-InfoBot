[CmdletBinding()]
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'

Write-Host 'Lib InfoBot Windows setup'
Write-Host 'This script preserves the existing Flask + MySQL architecture.'

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher (py) was not found. Install Python 3.11 or 3.12 first.'
}

if (-not (Test-Path '.\myenv\Scripts\python.exe')) {
    Write-Host 'Creating virtual environment: myenv'
    py -3.12 -m venv myenv
}

$python = Join-Path (Get-Location) 'myenv\Scripts\python.exe'

if (-not $SkipInstall) {
    & $python -m pip install --upgrade pip
    & $python -m pip install -r requirements.txt
}

if (-not (Test-Path '.\.env')) {
    Copy-Item '.\.env.example' '.\.env'
    Write-Host 'Created .env from .env.example. Add local values before starting Flask.'
}

Write-Host 'Checking the native MySQLdb extension...'
try {
    & $python -c "import MySQLdb; print('MySQLdb import OK')"
} catch {
    Write-Warning 'The native mysqlclient extension could not be imported.'
    Write-Warning 'If Windows reports that an Application Control policy blocked _mysql, contact the system administrator.'
    Write-Warning 'Do not copy untrusted DLL files and do not replace MySQL with SQLite.'
}

Write-Host ''
Write-Host 'Next steps:'
Write-Host '1. Start the existing MySQL service from XAMPP.'
Write-Host '2. Confirm .env matches the existing database.'
Write-Host '3. Run: myenv\Scripts\python.exe app.py'
Write-Host '4. Open: http://127.0.0.1:5000/'
