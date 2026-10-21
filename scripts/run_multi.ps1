# Medium model (teacher), then the 68M trained directly for comparison, then the 68M distilled from the medium.
Set-Location C:\Users\jared\qm-training
$env:PYTHONIOENCODING = 'utf-8'
$py = ".\.venv\Scripts\python.exe"
& $py scripts\spans.py collect *>> logs\multi.log
& $py scripts\train_multi.py teach --base jhu-clsp/ettin-encoder-400m --name m400 --epochs 4 *>> logs\multi.log
& $py scripts\train_multi.py direct --base jhu-clsp/ettin-encoder-68m --name d68 --epochs 4 *>> logs\multi.log
& $py scripts\train_multi.py distill --base jhu-clsp/ettin-encoder-68m --teacher work\multi\m400.pt --name s68 *>> logs\multi.log
"DONE" | Out-File -Append logs\multi.log
