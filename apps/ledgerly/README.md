# Ledgerly

Ledgerly is the paycheck-first budget desktop app. This folder is its source snapshot and update build input inside the shared `VeyrStudio/DesktopAppUpdates` repository.

The Windows workflow rebuilds the source snapshot, creates the Tauri NSIS installer, publishes a `ledgerly-vX.Y.Z` GitHub Release, computes the installer SHA-256, and writes the current update manifest to `/ledgerly/manifest.json`.

Ledgerly checks that manifest automatically when it opens (unless automatic checks are turned off in Settings) and also has a manual **Check for Updates** button. An update is only launched after the downloaded installer matches the published SHA-256 and its URL belongs to Ledgerly's GitHub release channel.

Saved budgets, groceries, paycheck history, and settings are stored separately from the application-code files so app updates do not intentionally overwrite them.
