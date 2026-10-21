; Build with the native Windows runner's existing Inno Setup compiler.
; The caller supplies build/output/version/icon paths as preprocessor defines.
[Setup]
AppId={{D5A712BF-CA30-4CBC-9631-526C7614D96D}
AppName=VerseView Detector
AppVersion={#AppVersion}
AppPublisher=VerseView Detector contributors
DefaultDirName={localappdata}\Programs\VerseView Detector
DefaultGroupName=VerseView Detector
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDirectory}
OutputBaseFilename={#OutputName}
SetupIconFile={#AppIcon}
UninstallDisplayIcon={app}\VerseView Detector.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VerseView Detector"; Filename: "{app}\VerseView Detector.exe"

[Run]
Filename: "{app}\VerseView Detector.exe"; Description: "Open VerseView Detector"; Flags: nowait postinstall skipifsilent
