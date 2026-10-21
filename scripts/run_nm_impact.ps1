# Impact: real-only vs staged with impact near-miss pairs, 68M then 400M, 3 seeds each.
Set-Location C:\Users\jared\qm-training
$py = ".\.venv\Scripts\python.exe"
foreach ($b in "jhu-clsp/ettin-encoder-68m", "jhu-clsp/ettin-encoder-400m") {
    foreach ($seed in 1, 2, 3) {
        & $py scripts\train_head.py --dim impact --base $b --arm real --seed $seed *>> logs\nm-impact.log
        & $py scripts\train_head.py --dim impact --base $b --arm staged --epochs 1 --sets nmimpact --tag nm --seed $seed *>> logs\nm-impact.log
    }
}
"DONE" | Out-File -Append logs\nm-impact.log
