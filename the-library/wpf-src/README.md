# The Library WPF migration

This is the compiled C# replacement for the existing PowerShell/WinForms interface.

- Reads and writes the existing `%LOCALAPPDATA%\CoverVault\Data\library.json` database.
- Uses the existing `%LOCALAPPDATA%\CoverVault\Data\Files` cover store.
- Preserves the independent `VeyrStudio/DesktopAppUpdates/the-library` update channel.
- Uses a self-contained, single-file `TheLibrary.exe`; the user does not need to install .NET or another runtime.
- Keeps `CoverVault.ps1` only as a tiny compatibility bridge for the existing shortcut during migration.

Full cover wraps are temporary sources. Only Back Cover, Spine, and Front Cover PNG panels are saved.
