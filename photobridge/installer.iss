#define V GetEnv("PHOTOBRIDGE_VERSION")
[Setup]
AppId={{776CE48B-6BB0-468C-B148-FB0D82FE412A}
AppName=PhotoBridge
AppVersion={#V}
DefaultDirName={localappdata}\Programs\PhotoBridge
DefaultGroupName=PhotoBridge
UninstallDisplayIcon={app}\PhotoBridge.exe
SetupIconFile=icon.ico
OutputDir=dist
OutputBaseFilename=PhotoBridge-Setup-{#V}
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; Flags: checkedonce
[Files]
Source: "dist\PhotoBridge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\PhotoBridge"; Filename: "{app}\PhotoBridge.exe"
Name: "{autodesktop}\PhotoBridge"; Filename: "{app}\PhotoBridge.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\PhotoBridge.exe"; Description: "Launch PhotoBridge"; Flags: nowait postinstall skipifsilent
