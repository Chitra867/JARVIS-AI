; JARVIS OS installer
; Compile with build-installer.ps1 from the repository root.

#define MyAppName "JARVIS OS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "JARVIS OS"
#define MyAppExeName "start-jarvis.ps1"

[Setup]
AppId={{EAF99255-7342-4EDE-93E8-7604B46862FB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\JARVIS OS
DefaultGroupName=JARVIS OS
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=JARVIS-OS-Setup-1.0.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=JARVIS OS
SetupLogging=yes
CloseApplications=no
RestartApplications=no

[Dirs]
Name: "{app}\server\data"

[Files]
Source: "..\start-jarvis.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\stop-jarvis.ps1"; DestDir: "{app}"; Flags: ignoreversion

; Runtime backend. Do not ship the developer venv, tests, caches, database,
; local secrets, or repository metadata.
Source: "..\server\*"; DestDir: "{app}\server";     Flags: ignoreversion recursesubdirs createallsubdirs;     Excludes: ".venv\*,tests\*,__pycache__\*,*.pyc,.pytest_cache\*,data\jarvis.db,.env,.env.*,*.log"

; Production HUD only. Node/npm are not required at runtime.
Source: "..\hud\dist\*"; DestDir: "{app}\hud\dist";     Flags: ignoreversion recursesubdirs createallsubdirs

; Runtime bootstrapper used by Setup and for repairs.
Source: "setup-runtime.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion

[Icons]
Name: "{group}\JARVIS OS";     Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe";     Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\start-jarvis.ps1""";     WorkingDir: "{app}"

Name: "{group}\Stop JARVIS OS";     Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe";     Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\stop-jarvis.ps1""";     WorkingDir: "{app}"

Name: "{autodesktop}\JARVIS OS";     Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe";     Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\start-jarvis.ps1""";     WorkingDir: "{app}";     Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe";     Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\setup-runtime.ps1""";     WorkingDir: "{app}";     Description: "Configure the JARVIS Python runtime";     StatusMsg: "Installing JARVIS Python dependencies...";     Flags: waituntilterminated

Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe";     Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\start-jarvis.ps1""";     WorkingDir: "{app}";     Description: "Launch JARVIS OS";     Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe";     Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\stop-jarvis.ps1""";     WorkingDir: "{app}";     Flags: runhidden waituntilterminated skipifdoesntexist;     RunOnceId: "StopJarvisBeforeUninstall"
