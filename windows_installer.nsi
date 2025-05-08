; SimpleRename Installer Script
!define APPNAME "SimpleRename"
!define COMPANYNAME "simplerename"
!define DESCRIPTION "A lightweight file renaming tool"
!define VERSION "0.0.4"
!define INSTALLSIZE 20000

; Include Modern UI
!include "MUI2.nsh"

; General
Name "${APPNAME}"
OutFile "SimpleRenameSetup.exe"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "Software\${APPNAME}" "Install_Dir"

; Interface Configuration
!define MUI_ICON "resources\icons\simplerename.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_ABORTWARNING

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer sections
Section "Install"
    SetOutPath $INSTDIR
    
    ; Application files
    File "dist\SimpleRename.exe"
    
    ; Create Program Files directory structure
    CreateDirectory "$INSTDIR\resources"
    CreateDirectory "$INSTDIR\resources\icons"
    
    ; Copy resources
    File /r "resources\icons\simplerename.ico" "$INSTDIR\resources\icons\"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\${APPNAME}"
    CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\SimpleRename.exe"
    CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\SimpleRename.exe"
    
    ; Write uninstaller information to registry
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayIcon" "$INSTDIR\resources\icons\simplerename.ico"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "URLInfoAbout" "https://github.com/simplerename/simplerename"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoRepair" 1
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; Uninstaller section
Section "Uninstall"
    ; Remove application files
    Delete "$INSTDIR\SimpleRename.exe"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Remove resources
    RMDir /r "$INSTDIR\resources"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
    Delete "$DESKTOP\${APPNAME}.lnk"
    RMDir "$SMPROGRAMS\${APPNAME}"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
    DeleteRegKey HKLM "Software\${APPNAME}"
    
    ; Remove installation directory
    RMDir "$INSTDIR"
SectionEnd