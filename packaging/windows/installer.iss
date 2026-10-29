; Inno Setup script — compile on Windows after PyInstaller build.
; Paths assume dist\justconvertit from repo root.
; Offline-first: no updater helpers, no download URLs, no AppMutex phone-home.

#define MyAppName "justconvertit"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "justconvertit Contributors"
#define MyAppExeName "justconvertit.exe"

[Setup]
AppId={{A8C3E2F1-4B7D-4E9A-9C21-JUSTCONVERT01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppSupportURL=
AppUpdatesURL=
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=justconvertit-{#MyAppVersion}-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayName={#MyAppName}
SetupIconFile=omniconvert.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
InfoBeforeFile=..\..\docs\PRIVACY.md
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "..\..\dist\justconvertit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\docs\INSTALL.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docs\PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docs\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch justconvertit"; Flags: nowait postinstall skipifsilent
