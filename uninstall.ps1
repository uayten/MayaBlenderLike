# Removes the module registration. The Blender_Style hotkey set stays in Maya's
# preferences; switch back to Maya_Default in the Hotkey Editor if needed.
$documents = [Environment]::GetFolderPath('MyDocuments')
$modFile = Join-Path $documents 'maya\modules\MayaBlenderLike.mod'

if (Test-Path $modFile) {
    Remove-Item $modFile
    Write-Host "Removed: $modFile"
} else {
    Write-Host "Not installed: $modFile not found"
}
