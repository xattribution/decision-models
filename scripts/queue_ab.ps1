param([string]$dim = "content", [string]$base = "jhu-clsp/ettin-encoder-68m")
# Wait until no other A/B runner is going (checked by the runner script, not the python between seeds), then run.
while (Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like "*run_ab.ps1*" -and $_.ProcessId -ne $PID }) {
    Start-Sleep 20
}
& C:\Users\jared\qm-training\scripts\run_ab.ps1 $dim $base
