# The Ledger

The Ledger is a discreet, local-first Windows lecture capture and transcription app for VeyrStudio.

## Working milestone

This project currently includes:

- the approved dark-academia interface and icon;
- Today, Classes, Notebook, Review, Search, and Settings;
- manually entered class schedules and automatic `Date • Time • Class` lecture titles;
- incremental, crash-recoverable recording files;
- microphone testing, pause/resume, timestamped notes, and lecture markers;
- local JSON data storage outside the installation folder;
- import, transcript display, basic export, in-app notification badge, and no Windows notification banners;
- local whisper.cpp transcription integration when built by the Windows workflow;
- a self-contained NSIS installer workflow that bundles Electron, FFmpeg, whisper.cpp, and the balanced English model;
- automatic verified update staging and a Force Update path.

## Important milestone boundary

The first milestone does not yet implement trained professor voice matching, robust multi-speaker diarization, Word/PDF export, full transcript correction tooling, or advanced semantic review generation. The interfaces and data model are prepared for those additions, but they must be completed and tested before the app is treated as production-ready for school.

## Local development

```powershell
npm install
npm test
npm start
```

Development mode can record, import, store, and organize lectures. Local transcription becomes available when `whisper-cli`, FFmpeg, and a supported model are placed under `resources/` as described in those folders.

## Windows installer

The GitHub Actions workflow builds `TheLedgerSetup-<version>.exe`. It downloads and bundles all required transcription components during the build so the end user installs only The Ledger.

The app uses a normal Windows title bar and stores user data beneath `VeyrStudio\TheLedger\Data`, separate from application files and updates.
