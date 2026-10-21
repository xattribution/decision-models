# Does stripping the leading dash help on the val source (which never has one)? 68M then 400M, all three dims.
Set-Location C:\Users\jared\qm-training
$py = ".\.venv\Scripts\python.exe"
$sets = @{ "structure" = "structure,nmstruct"; "content" = "content,nmcontent"; "impact" = "nmimpact" }
foreach ($b in "jhu-clsp/ettin-encoder-68m", "jhu-clsp/ettin-encoder-400m") {
    foreach ($dim in "structure", "content", "impact") {
        & $py scripts\train_head.py --dim $dim --base $b --real r5 --arm staged --epochs 1 --real-epochs 4 --sets $sets[$dim] --tag r5norm --norm --seed 1 *>> logs\norm.log
    }
}
"DONE" | Out-File -Append logs\norm.log
