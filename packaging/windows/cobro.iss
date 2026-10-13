; Inno Setup script — builds Cobro-Setup.exe (per-user install, no admin needed)
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
AppId={{C850227F-94F4-4A15-8B75-ACF38F960B4D}
AppName=Cobro
AppVersion={#MyAppVersion}
AppPublisher=Cobro
DefaultDirName={localappdata}\Programs\Cobro
DefaultGroupName=Cobro
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=Cobro-Setup
SetupIconFile=..\..\build\icon.ico
UninstallDisplayIcon={app}\Cobro.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\..\dist\Cobro\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Cobro"; Filename: "{app}\Cobro.exe"
Name: "{userdesktop}\Cobro"; Filename: "{app}\Cobro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Cobro.exe"; Description: "Open Cobro now"; Flags: nowait postinstall skipifsilent
