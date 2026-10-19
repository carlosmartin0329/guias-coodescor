# Configura una tarea programada en Windows para ejecutar la exportación a Supabase cada 15 minutos
# Requiere ejecutar PowerShell como Administrador

$taskName = "Coodescor - Exportar a Supabase (cada 15 min)"
$scriptPath = "$PSScriptRoot\exportar_a_supabase.py"
$pythonExe = "py"
$workingDir = "$PSScriptRoot"

# Verificar que existe el archivo .env
$envFile = Join-Path $workingDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Warning "No se encontró .env. Copia .env.example a .env y configura SUPABASE_URL y SUPABASE_KEY."
}

# Crear la acción de la tarea
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument $scriptPath -WorkingDirectory $workingDir

# Disparador: cada 15 minutos, repetir indefinidamente, iniciar ahora
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -Repetition (New-ScheduledTaskRepetitionInterval -Minutes 15) -Duration ([timespan]::MaxValue)

# Configuración de la tarea
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

$principal = New-ScheduledTaskPrincipal -UserId (whoami) -LogonType S4U -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force

Write-Host "Tarea programada creada: $taskName"
Write-Host "Se ejecutará cada 15 minutos usando: $scriptPath"
