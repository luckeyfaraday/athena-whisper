; Inno Setup script for the Athena Dictate Windows installer.
; Compiled by build/build-windows.ps1 after PyInstaller produces
; dist\Athena Dictate\. Output: dist\Athena Dictate Setup.exe
;
; Per-user install (no admin required). Run manually with:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\windows-installer.iss

#define MyAppName "Athena Dictate"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Athena"
#define MyAppExeName "Athena Dictate.exe"

[Setup]
AppId={{8F3A6C1E-3B2D-4E5A-9C7F-1A2B3C4D5E6F}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Install per-user so no administrator prompt is needed.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
OutputDir=..\dist
OutputBaseFilename=Athena Dictate Setup
SetupIconFile=icons\athena.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
; The trailing "\*" copies the whole PyInstaller one-folder output.
Source: "..\dist\Athena Dictate\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupFlags: unchecked

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
