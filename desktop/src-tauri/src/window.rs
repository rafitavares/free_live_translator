use tauri::{AppHandle, Manager};

#[cfg(target_os = "macos")]
fn activate_macos_application(app: &AppHandle) -> Result<(), String> {
    app.run_on_main_thread(|| {
        let Some(main_thread) = objc2::MainThreadMarker::new() else {
            return;
        };
        let application = objc2_app_kit::NSApplication::sharedApplication(main_thread);
        #[allow(deprecated)]
        application.activateIgnoringOtherApps(true);
    })
    .map_err(|error| error.to_string())
}

pub fn show_control_window(app: &AppHandle) -> Result<(), String> {
    let window = app
        .get_webview_window("control")
        .ok_or_else(|| "The Church Cap control window is unavailable.".to_string())?;
    #[cfg(target_os = "macos")]
    app.show().map_err(|error| error.to_string())?;
    window.unminimize().map_err(|error| error.to_string())?;
    window.show().map_err(|error| error.to_string())?;
    // Centre only after the native window is visible. Some macOS monitor APIs
    // cannot place a hidden window and must not prevent the window reopening.
    window.center().map_err(|error| error.to_string())?;
    window.set_focus().map_err(|error| error.to_string())?;
    #[cfg(target_os = "macos")]
    activate_macos_application(app)?;
    Ok(())
}

#[tauri::command]
pub fn show_controls(app: AppHandle) -> Result<(), String> {
    show_control_window(&app)
}
