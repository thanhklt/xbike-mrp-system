#requires -Version 5.1
<#
.SYNOPSIS
Starts the backend and frontend together. Press Ctrl+C to stop both.
.DESCRIPTION
Run .\start-dev.ps1 from PowerShell. Requires installed Poetry/backend
dependencies, Node.js/frontend dependencies, and a running PostgreSQL instance.
Backend configuration is read from backend/app/config/config.yml.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$backendDirectory = Join-Path $PSScriptRoot 'backend'
$frontendDirectory = Join-Path $PSScriptRoot 'frontend'
$poetry = (Get-Command poetry.exe -CommandType Application -TotalCount 1 -ErrorAction Stop).Source
$npm = (Get-Command npm.cmd -CommandType Application -TotalCount 1 -ErrorAction Stop).Source
$powerShell = (Get-Process -Id $PID).Path

if (-not (Test-Path -LiteralPath (Join-Path $backendDirectory 'pyproject.toml'))) {
    throw "Backend project not found: $backendDirectory"
}
if (-not (Test-Path -LiteralPath (Join-Path $frontendDirectory 'node_modules/vite/bin/vite.js'))) {
    throw 'Frontend dependencies are missing. Run npm ci in the frontend directory first.'
}

$servers = @(
    @{
        Name = 'Backend'
        Directory = $backendDirectory
        Command = "& '$($poetry.Replace("'", "''"))' run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
    },
    @{
        Name = 'Frontend'
        Directory = $frontendDirectory
        Command = "& '$($npm.Replace("'", "''"))' run dev -- --strictPort"
    }
)
$serverProcesses = @()

try {
    foreach ($server in $servers) {
        $command = "`$ErrorActionPreference = 'Stop'; $($server.Command); exit `$LASTEXITCODE"
        $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
        $serverProcesses += Start-Process -FilePath $powerShell -WorkingDirectory $server.Directory `
            -ArgumentList '-NoProfile', '-EncodedCommand', $encodedCommand -NoNewWindow -PassThru
        Write-Host "Starting $($server.Name)..."
    }

    Write-Host 'Backend:  http://localhost:8000/docs'
    Write-Host 'Frontend: http://localhost:5173'
    Write-Host 'Press Ctrl+C to stop both servers.'

    while ($true) {
        for ($index = 0; $index -lt $serverProcesses.Count; $index++) {
            if ($serverProcesses[$index].HasExited) {
                throw "$($servers[$index].Name) exited with code $($serverProcesses[$index].ExitCode). See the output above."
            }
        }
        Start-Sleep -Milliseconds 250
    }
}
finally {
    foreach ($serverProcess in $serverProcesses) {
        if (-not $serverProcess.HasExited) {
            # Stop only the process trees launched here, including reload workers.
            & "$env:SystemRoot\System32\taskkill.exe" /PID $serverProcess.Id /T /F
        }
    }
}
