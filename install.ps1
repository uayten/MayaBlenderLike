# Registers this folder as a Maya module for every installed Maya version.
# Writes <Documents>\maya\modules\MayaBlenderLike.mod pointing to this folder.
$repo = $PSScriptRoot
$documents = [Environment]::GetFolderPath('MyDocuments')
$modules = Join-Path $documents 'maya\modules'
$modFile = Join-Path $modules 'MayaBlenderLike.mod'

New-Item -ItemType Directory -Force -Path $modules | Out-Null
Set-Content -Path $modFile -Encoding ASCII -Value @(
    "+ MayaBlenderLike 1.0 $repo",
    "scripts: scripts"
)

Write-Host "Installed: $modFile"
Write-Host "Module folder: $repo"
Write-Host "Restart Maya to load it."
