; Inno Setup 6 — compile on Windows after PyInstaller:
;   pyinstaller --noconfirm --clean packaging/windows/omniconvert.spec
;   ISCC packaging/windows/installer.iss
;
; Friend-friendly defaults: per-user install (no admin), Start Menu + optional desktop icon.
; Offline-first: no updater, no download URLs, no phone-home.

#define MyAppName "JustConvertIt"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "JustConvertIt Contributors"
#define MyAppExeName "justconvertit.exe"

[Setup]
; Valid GUID required (hex only in each segment).
AppId={{A8C3E2F1-4B7D-4E9A-9C21-A1B2C3D4E5F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppSupportURL=
AppUpdatesURL=
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableReadyPage=no
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=JustConvertIt-{#MyAppVersion}-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user install — friends do not need Administrator.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayName={#MyAppName}
SetupIconFile=omniconvert.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoProductName={#MyAppName}
VersionInfoCompany={#MyAppPublisher}
CloseApplications=yes
RestartApplications=no
; Short privacy blurb instead of dumping full PRIVACY.md into the wizard.
InfoBeforeFile=install_info.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
Source: "..\..\dist\justconvertit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\docs\INSTALL.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docs\PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docs\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch JustConvertIt"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
