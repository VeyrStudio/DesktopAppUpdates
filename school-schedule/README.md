# School Schedule App update channel

This folder is reserved for the School Schedule App's independent update channel.

Planned update model:
- `appId`: `school-schedule`
- Independent semantic versioning
- Manifest-based update checks
- SHA-256 verification before applying updates
- Versioned payload parts hosted in this folder
- User schedule data stored outside the application/update payload so app updates cannot overwrite classes, work shifts, or meal-time data

A production `manifest.json` will be added with the first distributable build rather than publishing an empty/broken update manifest.
