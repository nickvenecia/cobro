; Inno Setup script — builds Saldo-Setup.exe (per-user install, no admin needed)
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
; The AppId the app has had since it was called Cobro: Windows sees Saldo as that same app, updated in place
; (one entry in Installed Apps, one uninstaller)
AppId={{C850227F-94F4-4A15-8B75-ACF38F960B4D}
AppName=Saldo
AppVersion={#MyAppVersion}
AppPublisher=Saldo
DefaultDirName={localappdata}\Programs\Saldo
DefaultGroupName=Saldo
UsePreviousGroup=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=Saldo-Setup
SetupIconFile=..\..\build\icon.ico
UninstallDisplayIcon={app}\Saldo.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\..\dist\Saldo\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
; Cobro's updater opens Cobro.exe once this installer is done: where the app was installed as Cobro, a copy of
; Saldo.exe answers to that name until the next update takes it away
Source: "..\..\dist\Saldo\Saldo.exe"; DestDir: "{app}"; DestName: "Cobro.exe"; Flags: ignoreversion; Check: FromCobro

[InstallDelete]
Type: files; Name: "{app}\Cobro.exe"; Check: not FromCobro
Type: filesandordirs; Name: "{app}\_internal\cobro"
; Cobro's own shortcuts: Saldo's take their place
Type: filesandordirs; Name: "{userprograms}\Cobro"
Type: files; Name: "{userdesktop}\Cobro.lnk"

[Icons]
Name: "{group}\Saldo"; Filename: "{app}\Saldo.exe"
Name: "{userdesktop}\Saldo"; Filename: "{app}\Saldo.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Saldo.exe"; Description: "Open Saldo now"; Flags: nowait postinstall skipifsilent

[Code]
var
  Looked, CobroThere: Boolean;

{ Updating a copy installed as Cobro: its Cobro.exe is there and no Saldo.exe yet. Decided once, the first time
  it's asked once the folder is known, before this installer has changed anything. }
function FromCobro: Boolean;
begin
  if not Looked then
  begin
    try
      CobroThere := FileExists(ExpandConstant('{app}\Cobro.exe')) and
        not FileExists(ExpandConstant('{app}\Saldo.exe'));
      Looked := True;
    except
      CobroThere := False;
    end;
  end;
  Result := CobroThere;
end;
