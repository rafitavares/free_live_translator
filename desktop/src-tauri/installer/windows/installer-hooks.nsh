!include nsDialogs.nsh

!define MUI_WELCOMEFINISHPAGE_BITMAP_STRETCH AspectFitHeight
!define MUI_HEADERIMAGE_BITMAP_STRETCH AspectFitHeight
!define MUI_HEADERIMAGE_UNBITMAP_STRETCH AspectFitHeight
!define MUI_INSTFILESPAGE_PROGRESSBAR colored

Var ChurchCapCudaCheckbox
Var ChurchCapInstallCuda
Var ChurchCapCudaTitleFont
Var ChurchCapCudaBodyFont
Var ChurchCapCudaHandoffLog

Page custom ChurchCapCudaPage ChurchCapCudaPageLeave

Function ChurchCapCudaPage
  ${If} ${Silent}
    Abort
  ${EndIf}
  ${GetOptions} $CMDLINE "/P" $0
  ${IfNot} ${Errors}
    Abort
  ${EndIf}

  !insertmacro MUI_HEADER_TEXT "Optional NVIDIA acceleration" "Choose whether Church Cap should prepare CUDA after installing."
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}

  CreateFont $ChurchCapCudaTitleFont "Segoe UI Semibold" 12 600
  CreateFont $ChurchCapCudaBodyFont "Segoe UI" 9 400

  ${NSD_CreateLabel} 0 0 100% 20u "Faster captions with a supported NVIDIA GPU"
  Pop $0
  SendMessage $0 ${WM_SETFONT} $ChurchCapCudaTitleFont 1

  ${NSD_CreateLabel} 0 24u 100% 46u "English captions work without CUDA. Church Cap can download about 1.1 GB of verified NVIDIA CUDA 12.4 and cuDNN 9 runtime files for this Windows account. Internet access and roughly 3 GB of temporary free space are required."
  Pop $0
  SendMessage $0 ${WM_SETFONT} $ChurchCapCudaBodyFont 1

  ${NSD_CreateCheckbox} 0 76u 100% 20u "Install optional NVIDIA CUDA acceleration"
  Pop $ChurchCapCudaCheckbox
  IfFileExists "$APPDATA\Church Cap\data\cuda-install-requested.flag" 0 +2
    ${NSD_Check} $ChurchCapCudaCheckbox
  IfFileExists "$APPDATA\Church Cap\data\cuda-install-requested.flag" +2 0
    ${NSD_Uncheck} $ChurchCapCudaCheckbox
  SendMessage $ChurchCapCudaCheckbox ${WM_SETFONT} $ChurchCapCudaBodyFont 1

  ${NSD_CreateLabel} 0 102u 100% 34u "Use this only with a supported NVIDIA GPU. If setup cannot finish the download, Church Cap will show its progress and retry after first launch. You can also repair CUDA later from Performance settings."
  Pop $0
  SendMessage $0 ${WM_SETFONT} $ChurchCapCudaBodyFont 1

  nsDialogs::Show
FunctionEnd

Function ChurchCapCudaPageLeave
  ${NSD_GetState} $ChurchCapCudaCheckbox $0
  StrCpy $ChurchCapInstallCuda 0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $ChurchCapInstallCuda 1
    CreateDirectory "$APPDATA\Church Cap\data"
    CreateDirectory "$APPDATA\Church Cap\logs"
    ClearErrors
    FileOpen $1 "$APPDATA\Church Cap\data\cuda-install-requested.flag" w
    ${If} ${Errors}
      MessageBox MB_OK|MB_ICONSTOP "Church Cap could not save the optional CUDA request in your application-data folder. Setup will continue without CUDA; use Performance > Install / repair CUDA runtime after Church Cap opens."
      StrCpy $ChurchCapInstallCuda 0
    ${Else}
      FileWrite $1 "Requested from the Church Cap installer.$\r$\n"
      FileClose $1
      FileOpen $ChurchCapCudaHandoffLog "$APPDATA\Church Cap\logs\cuda-installer-handoff.log" a
      ${IfNot} ${Errors}
        FileWrite $ChurchCapCudaHandoffLog "CUDA selected; durable request marker created.$\r$\n"
        FileClose $ChurchCapCudaHandoffLog
      ${EndIf}
    ${EndIf}
  ${Else}
    Delete "$APPDATA\Church Cap\data\cuda-install-requested.flag"
  ${EndIf}
FunctionEnd

!macro NSIS_HOOK_POSTINSTALL
  IfFileExists "$APPDATA\Church Cap\data\cuda-install-requested.flag" 0 ChurchCapCudaDone
    DetailPrint "Preparing verified NVIDIA CUDA acceleration for Church Cap..."
    SetDetailsView show
    SetOutPath "$INSTDIR\engine\church-cap-engine"
    nsExec::ExecToLog '"$INSTDIR\engine\church-cap-engine\church-cap-engine.exe" --install-windows-cuda-runtime'
    Pop $0
    FileOpen $ChurchCapCudaHandoffLog "$APPDATA\Church Cap\logs\cuda-installer-handoff.log" a
    ${IfNot} ${Errors}
      FileWrite $ChurchCapCudaHandoffLog "Frozen CUDA helper exit code: $0.$\r$\n"
      FileClose $ChurchCapCudaHandoffLog
    ${EndIf}
    ${If} $0 = 0
      IfFileExists "$APPDATA\Church Cap\cuda-runtime\bin\cudart64_12.dll" 0 ChurchCapCudaDeferred
      IfFileExists "$APPDATA\Church Cap\cuda-runtime\bin\cublas64_12.dll" 0 ChurchCapCudaDeferred
      IfFileExists "$APPDATA\Church Cap\cuda-runtime\bin\cublasLt64_12.dll" 0 ChurchCapCudaDeferred
      IfFileExists "$APPDATA\Church Cap\cuda-runtime\bin\cudnn64_9.dll" 0 ChurchCapCudaDeferred
      Delete "$APPDATA\Church Cap\data\cuda-install-requested.flag"
      DetailPrint "Verified NVIDIA CUDA acceleration is ready."
      FileOpen $ChurchCapCudaHandoffLog "$APPDATA\Church Cap\logs\cuda-installer-handoff.log" a
      ${IfNot} ${Errors}
        FileWrite $ChurchCapCudaHandoffLog "Required CUDA DLLs verified; request complete.$\r$\n"
        FileClose $ChurchCapCudaHandoffLog
      ${EndIf}
      Goto ChurchCapCudaDone
    ${EndIf}
    ChurchCapCudaDeferred:
      DetailPrint "CUDA preparation was deferred to Church Cap first launch."
      MessageBox MB_OK|MB_ICONINFORMATION "Church Cap installed successfully. The optional CUDA download did not finish, so Church Cap will safely retry it after first launch. Keep Church Cap open and review Performance settings for progress."
    ChurchCapCudaDone:
!macroend
