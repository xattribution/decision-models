param([string]$dim = "structure", [string]$base = "jhu-clsp/ettin-encoder-68m")
Set-Location C:\Users\jared\qm-training
$py = ".\.venv\Scripts\python.exe"
foreach ($seed in 1, 2, 3) {
    if (-not ($dim -eq "structure" -and $seed -eq 1 -and $base -like "*68m")) {
        & $py scripts\train_head.py --dim $dim --arm synth --epochs 2 --seed $seed --base $base *>> "logs\ab-$dim.log"
    }
    & $py scripts\train_head.py --dim $dim --arm real --epochs 30 --seed $seed --base $base *>> "logs\ab-$dim.log"
    & $py scripts\train_head.py --dim $dim --arm both --epochs 2 --seed $seed --base $base *>> "logs\ab-$dim.log"
}
"DONE $base" | Out-File -Append "logs\ab-$dim.log"
