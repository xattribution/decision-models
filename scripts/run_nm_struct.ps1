# Structure: staged training with near-miss pairs, alone and with the ladders; 68M then 400M.
# Waits for any other run_*.ps1 runner first.
Set-Location C:\Users\jared\qm-training
while (Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like "*run_nm_content.ps1*" -or $_.CommandLine -like "*run_ab.ps1*" -or $_.CommandLine -like "*run_mix.ps1*" }) { Start-Sleep 20 }
$py = ".\.venv\Scripts\python.exe"
foreach ($seed in 1, 2, 3) {
    & $py scripts\train_head.py --dim structure --arm staged --epochs 1 --sets nmstruct --tag nm --seed $seed *>> logs\nm-struct.log
    & $py scripts\train_head.py --dim structure --arm staged --epochs 1 --sets structure,nmstruct --tag lad+nm --seed $seed *>> logs\nm-struct.log
}
foreach ($seed in 1, 2, 3) {
    $b = "jhu-clsp/ettin-encoder-400m"
    & $py scripts\train_head.py --dim structure --base $b --arm staged --epochs 1 --sets structure,nmstruct --tag lad+nm --seed $seed *>> logs\nm-struct.log
}
"DONE" | Out-File -Append logs\nm-struct.log
