# PhotoBridge

Windows desktop receiver and iPhone Safari website, in the shared DesktopAppUpdates repository.

## Install
Open the PhotoBridge GitHub Release (tag starting with photobridge-v) and run PhotoBridge-Setup-<version>.exe. No Python installation is needed. Launch PhotoBridge, click Start / Stop Receiver, open the displayed URL on your iPhone (same trusted Wi-Fi), select files and press Send to computer.

Use Verify Files on Windows before deleting anything from the iPhone. The website only receives the files Safari's picker supplies; it does not have unrestricted Photos-library access. Transfers are manual, copy-only and preserve uploaded file bytes.

## Build and updates
GitHub Actions workflow: .github/workflows/build-photobridge.yml. The workflow produces a Windows installer, publishes a photobridge-v* GitHub Release and writes a PhotoBridge-only SHA256-protected update channel to photobridge/latest.json. The desktop app checks that channel automatically on opening and offers updates.

## Security
The receiver uses a temporary secret URL on the local network, but uploads use HTTP, not encrypted HTTPS. Only use trusted private Wi-Fi; stop the receiver when done. Anyone who obtains the secret link and can reach the receiver can upload files.
