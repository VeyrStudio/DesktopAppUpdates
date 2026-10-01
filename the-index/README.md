# The Index — update channel

This folder reserves a separate update channel for **The Index**, the Windows character-archive app.

- Repository: `VeyrStudio/DesktopAppUpdates`
- App identifier: `the-index`
- Release tag pattern: `the-index-v<version>` (e.g. `the-index-v0.1.0`)
- Installer asset pattern: `TheIndexSetup-<version>.exe`
- Update manifest: `the-index/latest.json`

Until the first Windows installer is built, published and tested, the manifest deliberately has a null version and download URL. Publishing a verified installer requires updating its version, URL and SHA-256 together. The updater must read **only this manifest** and never treat another app's repository-wide latest release as an update for The Index.

Character data must stay under the app's user-data directory, outside the installation folder. Do not overwrite Ledgerly or other app directories, workflows, manifests or releases.
