# Content: staged training with near-miss pairs, alone and with the ladders; 68M then 400M.
Set-Location C:\Users\jared\qm-training
$py = ".\.venv\Scripts\python.exe"
foreach ($seed in 1, 2, 3) {
    & $py scripts\train_head.py --dim content --arm staged --epochs 1 --sets nmcontent --tag nm --seed $seed *>> logs\nm-content.log
    & $py scripts\train_head.py --dim content --arm staged --epochs 1 --sets content,nmcontent --tag lad+nm --seed $seed *>> logs\nm-content.log
}
foreach ($seed in 1, 2, 3) {
    $b = "jhu-clsp/ettin-encoder-400m"
    & $py scripts\train_head.py --dim content --base $b --arm real --seed $seed *>> logs\nm-content.log
    & $py scripts\train_head.py --dim content --base $b --arm staged --epochs 1 --sets content,nmcontent --tag lad+nm --seed $seed *>> logs\nm-content.log
}
"DONE" | Out-File -Append logs\nm-content.log
