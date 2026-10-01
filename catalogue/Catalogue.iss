#define AppName "Catalogue"
#define AppVersion "1.0.0"
[Setup]
AppId={{CB3CF2AA-6C53-49F9-9189-D5243BBC2156}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=VeyrStudio
DefaultDirName={localappdata}\Programs\Catalogue
DefaultGroupName=Catalogue
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer
OutputBaseFilename=Catalogue-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\Catalogue.exe
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
CloseApplications=yes
[Files]
Source: "dist\Catalogue\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\CatalogueReminder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\Catalogue"; Filename: "{app}\Catalogue.exe"
Name: "{autodesktop}\Catalogue"; Filename: "{app}\Catalogue.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
[Run]
Filename: "{app}\Catalogue.exe"; Description: "Launch Catalogue"; Flags: nowait postinstall skipifsilent
