$TaskName = "BMS Local Services"
$Distro = "Ubuntu"
$ProjectPath = "/path/to/BMS"
$StartupCmd = Join-Path ([Environment]::GetFolderPath("Startup")) "bms-local-services.cmd"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "Removed: $TaskName"
} else {
  Write-Host "Task not found: $TaskName"
}

if (Test-Path $StartupCmd) {
  Remove-Item $StartupCmd -Force
  Write-Host "Removed: $StartupCmd"
}

try {
  wsl.exe -d $Distro -- bash -lc "cd '$ProjectPath' && bash scripts/stop_local_services.sh"
  Write-Host "Stopped current BMS local services in WSL."
} catch {
  Write-Host "Could not stop current BMS local services in WSL: $($_.Exception.Message)"
}
