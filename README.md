# DesktopAppUpdates

Remote update feeds for the desktop apps.

Each app has its own independent channel:

- `the-index/` — The Index
- `the-library/` — The Library
- `the-register/` — The Register
- `the-cipher/` — The Cipher

Future apps get their own folder and manifest in this same repository.

The installed apps keep user data outside their application-code folders, so updates replace application files only and do not overwrite saved user data.
