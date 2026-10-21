# Staged (synthetic then real) and down-weighted mix (synthetic x0.2), 3 seeds each.
Set-Location C:\Users\jared\qm-training
$py = ".\.venv\Scripts\python.exe"
$jobs = @(@("structure", "jhu-clsp/ettin-encoder-68m"), @("content", "jhu-clsp/ettin-encoder-68m"), @("structure", "jhu-clsp/ettin-encoder-400m"))
foreach ($j in $jobs) {
    foreach ($seed in 1, 2, 3) {
        & $py scripts\train_head.py --dim $j[0] --base $j[1] --arm staged --epochs 1 --seed $seed *>> logs\mix.log
        & $py scripts\train_head.py --dim $j[0] --base $j[1] --arm both --sw 0.2 --epochs 2 --seed $seed *>> logs\mix.log
    }
}
"DONE" | Out-File -Append logs\mix.log
