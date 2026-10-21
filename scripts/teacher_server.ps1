# Starts a private Ollama server for labeling on 127.0.0.1:11435, separate
# from the Ollama app (11434), with 8 requests at a time. Local only.
$env:OLLAMA_HOST = "127.0.0.1:11435"
$env:OLLAMA_NUM_PARALLEL = "8"
$env:OLLAMA_FLASH_ATTENTION = "1"
$env:OLLAMA_KV_CACHE_TYPE = "q8_0"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$log = "C:\Users\jared\qm-training\logs\teacher-server.log"
Start-Process -WindowStyle Hidden -FilePath "ollama" -ArgumentList "serve" -RedirectStandardError $log -RedirectStandardOutput "$log.out"
Start-Sleep -Seconds 3
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:11435/api/version).Content
