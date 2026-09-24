; Inno Setup installer for Mai AI Daemon
; Build the binary first with: python scripts/build_daemon.py
; Then compile with Inno Setup: iscc scripts/installer.iss

#define MyAppName "Mai AI"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Mai AI Project"
#define MyAppURL "http://localhost:8000"
#define MyAppExeName "mai-daemon.exe"

[Setup]
AppId={{B8F4A3D2-1C5E-4A7B-9D6F-2E8C1A3B5D7F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=MaiAI-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Run Mai AI at Windows startup"; GroupDescription: "Startup options"; Flags: checkedonce

[Files]
Source: "..\dist\mai-daemon\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: ""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "MaiAI"; ValueData: "{app}\{#MyAppExeName}"; Tasks: "startup"; Flags: uninsdeletevalue

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--uninstall"; Flags: runhidden
