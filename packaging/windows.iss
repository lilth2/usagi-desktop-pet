#define AppVersion "1.0.1"
[Setup]
AppId={{D23FE866-3582-4542-A01A-61BB0702A413}
AppName=吉伊卡哇桌宠
AppVersion={#AppVersion}
AppPublisher=ChiikawaPet
DefaultDirName={localappdata}\Programs\ChiikawaPet
DefaultGroupName=吉伊卡哇桌宠
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\deliverables
OutputBaseFilename=ChiikawaPet-Windows-Setup
SetupIconFile=..\assets\chiikawa\processed\icon.ico
UninstallDisplayIcon={app}\ChiikawaPet.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: chinesesimplified; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: english; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; Flags: unchecked

[Files]
Source: "..\dist\ChiikawaPet.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "使用说明.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "使用说明.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\吉伊卡哇桌宠"; Filename: "{app}\ChiikawaPet.exe"
Name: "{group}\使用说明"; Filename: "{app}\使用说明.html"
Name: "{group}\卸载吉伊卡哇桌宠"; Filename: "{uninstallexe}"
Name: "{autodesktop}\吉伊卡哇桌宠"; Filename: "{app}\ChiikawaPet.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ChiikawaPet.exe"; Description: "启动吉伊卡哇桌宠"; Flags: nowait postinstall skipifsilent
Filename: "{app}\使用说明.html"; Description: "打开使用说明"; Flags: shellexec postinstall skipifsilent unchecked
