Param(
    [string]$Source = "codigos pagina",
    [string]$Target = "www"
)

Write-Host "Sincronizando contenido de '$Source' a '$Target'..."

if (-not (Test-Path $Target)) {
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
}

robocopy "$Source" "$Target" /E /MIR /XD "android" "ios" "node_modules" "storage" ".git" ".next" ".out" ".cache"

if ($LASTEXITCODE -ge 8) {
    Write-Host "Robocopy devolvió error ($LASTEXITCODE). Revisa la salida." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Sync completado."

