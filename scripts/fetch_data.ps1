# Waits for the bank zip in Downloads\bullets to finish copying (size
# steady and the file no longer open elsewhere), then unpacks it with the
# loose .md and .pdf files into qm-training\data.
$src = "C:\Users\jared\Downloads\bullets"
$dst = "C:\Users\jared\qm-training\data"
$z = Join-Path $src "epr-bank-2026-10-20.zip"
$last = -1; $stable = 0; $free = $false
for ($i = 0; $i -lt 240; $i++) {
  $n = (Get-Item $z).Length
  $free = $false
  try { $f = [System.IO.File]::Open($z, 'Open', 'Read', 'None'); $f.Close(); $free = $true } catch {}
  if ($n -gt 0 -and $n -eq $last -and $free) { $stable++ } else { $stable = 0 }
  if ($stable -ge 3) { break }
  $last = $n; Start-Sleep -Seconds 5
}
"zip bytes: $((Get-Item $z).Length), free: $free"
if (-not $free) { "still in use; stopping"; exit 1 }
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
New-Item -ItemType Directory -Force $dst | Out-Null
Expand-Archive -Force $z $dst
Copy-Item (Join-Path $src "*.md") $dst -Force
New-Item -ItemType Directory -Force (Join-Path $dst "refs") | Out-Null
Copy-Item (Join-Path $src "*.pdf") (Join-Path $dst "refs") -Force
Get-ChildItem -Recurse $dst | Select-Object FullName, Length | Format-Table -AutoSize | Out-String -Width 250
