$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --onefile --windowed --name ChiikawaPet --icon 'assets/chiikawa/processed/icon.ico' --add-data 'assets/chiikawa/processed;assets/chiikawa/processed' desktop_pet.py
if ($LASTEXITCODE -ne 0) { throw 'ChiikawaPet build failed' }
