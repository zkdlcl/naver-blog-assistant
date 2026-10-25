$TaskName = "BMS Local Services"
$Distro = "Ubuntu"
$ProjectPath = "/path/to/BMS"

$WslCommand = "wsl.exe -d $Distro -- bash -lc `"cd '$ProjectPath' && bash scripts/start_local_services.sh`""

try {
  $Action = New-ScheduledTaskAction `
    -Execute "wsl.exe" `
    -Argument "-d $Distro -- bash -lc `"cd '$ProjectPath' && bash scripts/start_local_services.sh`""

  $Trigger = New-ScheduledTaskTrigger -AtLogOn
  $Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

  Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Start BMS web app and watch ranker in WSL on Windows login." `
    -Force `
    -ErrorAction Stop

  Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  Write-Host "Registered scheduled task: $TaskName"
} catch {
  $StartupDir = [Environment]::GetFolderPath("Startup")
  $CmdPath = Join-Path $StartupDir "bms-local-services.cmd"
  Set-Content -Path $CmdPath -Value "@echo off`r`n$WslCommand`r`n" -Encoding ASCII
  Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$CmdPath`"" -WindowStyle Hidden
  Write-Host "Scheduled task failed, created Startup command instead: $CmdPath"
}

Write-Host "Open http://localhost:8000 after a few seconds."
