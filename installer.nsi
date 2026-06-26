; SimpleRename Installer Script

; Versao injetada pelo CI via /DVERSION=X.Y.Z
!ifndef VERSION
  !define VERSION "0.0.0-dev"
!endif

!define APPNAME "SimpleRename"
!define COMPANYNAME "LucasLiachi"
!define DESCRIPTION "Organizador de bibliotecas PDF para Windows"
!define INSTALLSIZE 30000

; Include Modern UI
!include "MUI2.nsh"

; General
Name "${APPNAME} ${VERSION}"
OutFile "SimpleRename-Setup-${VERSION}.exe"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "Software\${APPNAME}" "Install_Dir"

; Interface Configuration
!define MUI_ICON "resources\icons\simplerename.ico"
!define MUI_ABORTWARNING

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer section
Section "Install"
    SetOutPath "$INSTDIR"

    ; Application executable (built by PyInstaller into dist/)
    File "dist\SimpleRename.exe"

    ; Icon resource
    SetOutPath "$INSTDIR\resources\icons"
    File "resources\icons\simplerename.ico"
    SetOutPath "$INSTDIR"

    ; Shortcuts
    CreateDirectory "$SMPROGRAMS\${APPNAME}"
    CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\SimpleRename.exe"
    CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\SimpleRename.exe"

    ; Registry — uninstall entry
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME} ${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoModify" 1

    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; Uninstaller section
Section "Uninstall"
    Delete "$INSTDIR\SimpleRename.exe"
    Delete "$INSTDIR\uninstall.exe"
    RMDir /r "$INSTDIR\resources"
    Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
    Delete "$DESKTOP\${APPNAME}.lnk"
    RMDir "$SMPROGRAMS\${APPNAME}"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
    DeleteRegKey HKLM "Software\${APPNAME}"
    RMDir "$INSTDIR"
SectionEnd
