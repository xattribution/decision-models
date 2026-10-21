# Build the shipped file: safetensors, the Q8_0 GGUF (and an f32 one for the exact check), the reference, the checks.
Set-Location C:\Users\jared\qm-training
$env:PYTHONIOENCODING = 'utf-8'
$py = ".\.venv\Scripts\python.exe"
$o = "export\qm-decide"
New-Item -ItemType Directory -Force $o | Out-Null
& $py scripts\export_st.py work\multi\s68.pt "$o\small"
& $py scripts\export_st.py work\multi\m400.pt "$o\medium"
& $py scripts\convert_decision.py "$o\small" "$o\medium" --out "$o\qm-decide-Q8_0.gguf"
& $py scripts\convert_decision.py "$o\small" "$o\medium" --type f32 --out work\qm-decide-F32.gguf
& $py scripts\decide_reference.py "$o\small" "$o\medium" "$o\reference"
& $py scripts\check_decision.py work\qm-decide-F32.gguf "$o\reference"
& $py scripts\check_decision.py "$o\qm-decide-Q8_0.gguf" "$o\reference"
Get-FileHash "$o\qm-decide-Q8_0.gguf" -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  qm-decide-Q8_0.gguf" } | Out-File -Encoding ascii "$o\qm-decide-Q8_0.gguf.sha256"
"EXPORT DONE"
