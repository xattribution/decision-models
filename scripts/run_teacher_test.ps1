# Labels the 500 hand-set items with both candidate teachers, one after the other.
Set-Location C:\Users\jared\qm-training
$py = ".\.venv\Scripts\python.exe"
& $py scripts\label.py --model gpt-oss:20b --split test --workers 8 *> logs\label-test-gptoss.log
& $py scripts\label.py --model gemma3:27b --split test --workers 8 *> logs\label-test-gemma.log
