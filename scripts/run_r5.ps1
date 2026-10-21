# Train on the round 5 key (6.7K train bullets), test on its val split (1.5K, a source not in train),
# and report the old round 4 test too. Real-only vs staged (synthetic pairs, then real).
Set-Location C:\Users\jared\qm-training
$py = ".\.venv\Scripts\python.exe"
$sets = @{ "structure" = "structure,nmstruct"; "content" = "content,nmcontent"; "impact" = "nmimpact" }
foreach ($b in "jhu-clsp/ettin-encoder-68m", "jhu-clsp/ettin-encoder-400m") {
    foreach ($dim in "structure", "content", "impact") {
        & $py scripts\train_head.py --dim $dim --base $b --real r5 --arm real --real-epochs 4 --tag r5 --seed 1 *>> logs\r5.log
        & $py scripts\train_head.py --dim $dim --base $b --real r5 --arm staged --epochs 1 --real-epochs 4 --sets $sets[$dim] --tag r5 --seed 1 *>> logs\r5.log
    }
}
"DONE" | Out-File -Append logs\r5.log
