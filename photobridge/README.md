# PhotoBridge

Windows desktop app and iPhone Safari website for manual, local-Wi-Fi photo and video transfers.

## Planned distribution

- Windows installer (`.exe`) with bundled runtime (no separate Python install).
- GitHub-powered release updates from this shared `DesktopAppUpdates` repository.
- App-specific files, update configuration, and Windows build workflow must target `photobridge/`, without affecting the repository's other apps.

## Transfer behavior

User presses a button on the phone website to transfer selected media. Receiver verifies files; neither side deletes iPhone originals automatically.

## Status

This folder has been created. The existing PhotoBridge prototype and release-build source still need to be added here and the release workflow adapted to the shared repository before installer builds or automatic updates can work.
