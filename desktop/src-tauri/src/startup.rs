use std::path::Path;
#[cfg(any(target_os = "macos", test))]
use std::path::PathBuf;

use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RegistrationState {
    NotRegistered,
    Enabled,
    #[cfg(any(target_os = "macos", test))]
    RequiresApproval,
    #[cfg(any(target_os = "macos", test))]
    NotFound,
}

#[cfg(any(target_os = "macos", test))]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RegistrationRequest {
    NoChange(RegistrationState),
    Register,
    Unregister,
    OpenApproval,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct StartAtLoginStatus {
    pub available: bool,
    pub enabled: bool,
    pub requires_approval: bool,
    pub detail: String,
}

impl StartAtLoginStatus {
    fn unavailable(detail: impl Into<String>) -> Self {
        Self {
            available: false,
            enabled: false,
            requires_approval: false,
            detail: detail.into(),
        }
    }
}

fn status_from_registration(state: RegistrationState) -> StartAtLoginStatus {
    match state {
        RegistrationState::NotRegistered => StartAtLoginStatus {
            available: true,
            enabled: false,
            requires_approval: false,
            detail: "Church Cap will not start automatically when you sign in.".into(),
        },
        RegistrationState::Enabled => StartAtLoginStatus {
            available: true,
            enabled: true,
            requires_approval: false,
            detail: "Church Cap will start automatically after you sign in.".into(),
        },
        #[cfg(any(target_os = "macos", test))]
        RegistrationState::RequiresApproval => StartAtLoginStatus {
            available: true,
            enabled: false,
            requires_approval: true,
            detail: "Allow Church Cap in System Settings → General → Login Items.".into(),
        },
        // Apple defines NotFound as a generic Service Management lookup error;
        // it is not evidence that the running bundle is outside Applications.
        // Keep the control available so an explicit register request can create
        // or repair the main-app login item.
        #[cfg(any(target_os = "macos", test))]
        RegistrationState::NotFound => StartAtLoginStatus {
            available: true,
            enabled: false,
            requires_approval: false,
            detail: "Church Cap is not registered to start at login. Turn this on to ask macOS to register it."
                .into(),
        },
    }
}

#[cfg(any(target_os = "macos", test))]
fn registration_request(state: RegistrationState, enabled: bool) -> RegistrationRequest {
    match (enabled, state) {
        (true, RegistrationState::Enabled) => {
            RegistrationRequest::NoChange(RegistrationState::Enabled)
        }
        (true, RegistrationState::RequiresApproval) => RegistrationRequest::OpenApproval,
        (true, RegistrationState::NotRegistered | RegistrationState::NotFound) => {
            RegistrationRequest::Register
        }
        (false, RegistrationState::NotRegistered | RegistrationState::NotFound) => {
            RegistrationRequest::NoChange(RegistrationState::NotRegistered)
        }
        (false, RegistrationState::Enabled | RegistrationState::RequiresApproval) => {
            RegistrationRequest::Unregister
        }
    }
}

#[cfg(any(target_os = "macos", test))]
fn containing_app_bundle(executable: &Path) -> Option<PathBuf> {
    executable.ancestors().find_map(|ancestor| {
        let is_app = ancestor
            .extension()
            .is_some_and(|extension| extension.eq_ignore_ascii_case("app"));
        (is_app && ancestor.join("Contents/Info.plist").is_file()).then(|| ancestor.to_path_buf())
    })
}

#[cfg(target_os = "macos")]
fn current_app_bundle() -> Option<PathBuf> {
    std::env::current_exe()
        .ok()
        .and_then(|executable| containing_app_bundle(&executable))
}

#[cfg(target_os = "macos")]
fn macos_registration_state() -> StartAtLoginStatus {
    use objc2_service_management::{SMAppService, SMAppServiceStatus};

    if !objc2::available!(macos = 13.0) {
        return StartAtLoginStatus::unavailable("Start at login requires macOS 13 or later.");
    }
    if current_app_bundle().is_none() {
        return StartAtLoginStatus::unavailable(
            "Start at login becomes available after Church Cap is installed as an application.",
        );
    }

    // SAFETY: The availability check above guarantees SMAppService exists, and
    // mainAppService/status do not outlive their retained Objective-C object.
    let service = unsafe { SMAppService::mainAppService() };
    let state = match unsafe { service.status() } {
        SMAppServiceStatus::NotRegistered => RegistrationState::NotRegistered,
        SMAppServiceStatus::Enabled => RegistrationState::Enabled,
        SMAppServiceStatus::RequiresApproval => RegistrationState::RequiresApproval,
        SMAppServiceStatus::NotFound => RegistrationState::NotFound,
        _ => RegistrationState::NotFound,
    };
    status_from_registration(state)
}

#[cfg(target_os = "macos")]
fn set_macos_registration(enabled: bool) -> Result<StartAtLoginStatus, String> {
    use objc2_service_management::{SMAppService, SMAppServiceStatus};

    if !objc2::available!(macos = 13.0) {
        return Err("Start at login requires macOS 13 or later.".into());
    }
    if current_app_bundle().is_none() {
        return Err(
            "Start at login becomes available after Church Cap is installed as an application."
                .into(),
        );
    }

    // SAFETY: The checks above establish macOS 13 availability and a real
    // running app bundle before asking Service Management about the main app.
    let service = unsafe { SMAppService::mainAppService() };
    let state = unsafe { service.status() };
    let state = match state {
        SMAppServiceStatus::NotRegistered => RegistrationState::NotRegistered,
        SMAppServiceStatus::Enabled => RegistrationState::Enabled,
        SMAppServiceStatus::RequiresApproval => RegistrationState::RequiresApproval,
        SMAppServiceStatus::NotFound => RegistrationState::NotFound,
        _ => RegistrationState::NotFound,
    };

    match registration_request(state, enabled) {
        RegistrationRequest::NoChange(state) => return Ok(status_from_registration(state)),
        RegistrationRequest::OpenApproval => {
            // SAFETY: Apple provides this method for a login item whose user
            // consent is pending or was revoked in System Settings.
            unsafe { SMAppService::openSystemSettingsLoginItems() };
            return Ok(status_from_registration(
                RegistrationState::RequiresApproval,
            ));
        }
        RegistrationRequest::Register => {
            // SAFETY: The retained main-app service belongs to this signed
            // application bundle. register() is authoritative even when the
            // preceding status lookup returned NotFound.
            unsafe { service.registerAndReturnError() }.map_err(|error| {
                format!(
                    "macOS could not register Church Cap to start at login: {}",
                    error.localizedDescription()
                )
            })?;
        }
        RegistrationRequest::Unregister => {
            // SAFETY: The retained main-app service belongs to this signed
            // application bundle.
            unsafe { service.unregisterAndReturnError() }.map_err(|error| {
                format!(
                    "macOS could not remove Church Cap from login items: {}",
                    error.localizedDescription()
                )
            })?;
        }
    }

    Ok(macos_registration_state())
}

#[cfg(not(any(target_os = "macos", target_os = "windows")))]
fn platform_registration_state() -> StartAtLoginStatus {
    StartAtLoginStatus::unavailable("Start at login is awaiting validation on this platform build.")
}

#[cfg(target_os = "windows")]
const WINDOWS_RUN_KEY: &str = r"Software\Microsoft\Windows\CurrentVersion\Run";
#[cfg(target_os = "windows")]
const WINDOWS_RUN_VALUE: &str = "Church Cap";

#[cfg(target_os = "windows")]
fn windows_startup_command(executable: &Path) -> String {
    format!("\"{}\"", executable.display())
}

#[cfg(target_os = "windows")]
fn wide(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(std::iter::once(0)).collect()
}

#[cfg(target_os = "windows")]
fn read_windows_run_value() -> Result<Option<String>, String> {
    use windows_sys::Win32::Foundation::{ERROR_FILE_NOT_FOUND, ERROR_SUCCESS};
    use windows_sys::Win32::System::Registry::{
        HKEY, HKEY_CURRENT_USER, KEY_READ, REG_SZ, RegCloseKey, RegOpenKeyExW, RegQueryValueExW,
    };
    let mut key: HKEY = std::ptr::null_mut();
    let result = unsafe {
        RegOpenKeyExW(
            HKEY_CURRENT_USER,
            wide(WINDOWS_RUN_KEY).as_ptr(),
            0,
            KEY_READ,
            &mut key,
        )
    };
    if result == ERROR_FILE_NOT_FOUND {
        return Ok(None);
    }
    if result != ERROR_SUCCESS {
        return Err(format!(
            "Windows could not read the per-user startup key (error {result})."
        ));
    }
    let name = wide(WINDOWS_RUN_VALUE);
    let mut kind = 0;
    let mut bytes = 0;
    let query = unsafe {
        RegQueryValueExW(
            key,
            name.as_ptr(),
            std::ptr::null_mut(),
            &mut kind,
            std::ptr::null_mut(),
            &mut bytes,
        )
    };
    if query == ERROR_FILE_NOT_FOUND {
        unsafe { RegCloseKey(key) };
        return Ok(None);
    }
    if query != ERROR_SUCCESS || kind != REG_SZ {
        unsafe { RegCloseKey(key) };
        return Err(format!(
            "Windows could not read the Church Cap startup value (error {query})."
        ));
    }
    let mut buffer = vec![0u16; (bytes as usize).div_ceil(2)];
    let query = unsafe {
        RegQueryValueExW(
            key,
            name.as_ptr(),
            std::ptr::null_mut(),
            &mut kind,
            buffer.as_mut_ptr().cast(),
            &mut bytes,
        )
    };
    unsafe { RegCloseKey(key) };
    if query != ERROR_SUCCESS {
        return Err(format!(
            "Windows could not read the Church Cap startup value (error {query})."
        ));
    }
    if buffer.last() == Some(&0) {
        buffer.pop();
    }
    Ok(Some(String::from_utf16_lossy(&buffer)))
}

#[cfg(target_os = "windows")]
fn windows_registration_state() -> StartAtLoginStatus {
    let executable = match std::env::current_exe() {
        Ok(path) => path,
        Err(error) => {
            return StartAtLoginStatus::unavailable(format!(
                "Church Cap could not locate its executable: {error}"
            ));
        }
    };
    match read_windows_run_value() {
        Ok(Some(value)) if value == windows_startup_command(&executable) => {
            status_from_registration(RegistrationState::Enabled)
        }
        Ok(Some(_)) => StartAtLoginStatus {
            available: true,
            enabled: false,
            requires_approval: false,
            detail: "A stale Church Cap start-at-login entry was found. Turn this on to repair it."
                .into(),
        },
        Ok(None) => status_from_registration(RegistrationState::NotRegistered),
        Err(error) => StartAtLoginStatus::unavailable(error),
    }
}

#[cfg(target_os = "windows")]
fn set_windows_registration(enabled: bool) -> Result<StartAtLoginStatus, String> {
    use windows_sys::Win32::Foundation::{ERROR_FILE_NOT_FOUND, ERROR_SUCCESS};
    use windows_sys::Win32::System::Registry::{
        HKEY, HKEY_CURRENT_USER, KEY_SET_VALUE, REG_OPTION_NON_VOLATILE, REG_SZ, RegCloseKey,
        RegCreateKeyExW, RegDeleteValueW, RegSetValueExW,
    };
    let mut key: HKEY = std::ptr::null_mut();
    let mut disposition = 0;
    let result = unsafe {
        RegCreateKeyExW(
            HKEY_CURRENT_USER,
            wide(WINDOWS_RUN_KEY).as_ptr(),
            0,
            std::ptr::null_mut(),
            REG_OPTION_NON_VOLATILE,
            KEY_SET_VALUE,
            std::ptr::null(),
            &mut key,
            &mut disposition,
        )
    };
    if result != ERROR_SUCCESS {
        return Err(format!(
            "Windows could not open the per-user startup key (error {result})."
        ));
    }
    let name = wide(WINDOWS_RUN_VALUE);
    let result = if enabled {
        let executable = std::env::current_exe()
            .map_err(|error| format!("Church Cap could not locate its executable: {error}"))?;
        let value = wide(&windows_startup_command(&executable));
        unsafe {
            RegSetValueExW(
                key,
                name.as_ptr(),
                0,
                REG_SZ,
                value.as_ptr().cast(),
                (value.len() * 2) as u32,
            )
        }
    } else {
        unsafe { RegDeleteValueW(key, name.as_ptr()) }
    };
    unsafe { RegCloseKey(key) };
    if result != ERROR_SUCCESS && !(result == ERROR_FILE_NOT_FOUND && !enabled) {
        return Err(format!(
            "Windows could not update start at login (error {result})."
        ));
    }
    Ok(windows_registration_state())
}

#[tauri::command]
pub fn get_start_at_login() -> StartAtLoginStatus {
    #[cfg(target_os = "macos")]
    {
        macos_registration_state()
    }
    #[cfg(not(target_os = "macos"))]
    {
        #[cfg(target_os = "windows")]
        {
            windows_registration_state()
        }
        #[cfg(not(target_os = "windows"))]
        {
            platform_registration_state()
        }
    }
}

#[tauri::command]
pub fn set_start_at_login(enabled: bool) -> Result<StartAtLoginStatus, String> {
    #[cfg(target_os = "macos")]
    {
        set_macos_registration(enabled)
    }
    #[cfg(not(target_os = "macos"))]
    {
        #[cfg(target_os = "windows")]
        {
            set_windows_registration(enabled)
        }
        #[cfg(not(target_os = "windows"))]
        {
            let _ = enabled;
            Err(platform_registration_state().detail)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[cfg(target_os = "windows")]
    struct WindowsRunEntryCleanup;

    #[cfg(target_os = "windows")]
    impl Drop for WindowsRunEntryCleanup {
        fn drop(&mut self) {
            let _ = set_windows_registration(false);
        }
    }

    #[test]
    fn registration_states_have_honest_ui_semantics() {
        let enabled = status_from_registration(RegistrationState::Enabled);
        assert!(enabled.available);
        assert!(enabled.enabled);

        let approval = status_from_registration(RegistrationState::RequiresApproval);
        assert!(approval.available);
        assert!(!approval.enabled);
        assert!(approval.requires_approval);

        let lookup_error = status_from_registration(RegistrationState::NotFound);
        assert!(lookup_error.available);
        assert!(!lookup_error.enabled);
        assert!(!lookup_error.detail.contains("Applications"));
    }

    #[test]
    fn a_not_found_lookup_does_not_block_an_explicit_registration_request() {
        assert_eq!(
            registration_request(RegistrationState::NotFound, true),
            RegistrationRequest::Register
        );
        assert_eq!(
            registration_request(RegistrationState::NotFound, false),
            RegistrationRequest::NoChange(RegistrationState::NotRegistered)
        );
        assert_eq!(
            registration_request(RegistrationState::RequiresApproval, true),
            RegistrationRequest::OpenApproval
        );
    }

    #[test]
    fn only_an_executable_inside_a_real_app_bundle_is_accepted() {
        let temporary = TempDir::new().unwrap();
        let bundle = temporary.path().join("Church Cap.app");
        let executable = bundle.join("Contents/MacOS/church-cap-desktop");
        std::fs::create_dir_all(executable.parent().unwrap()).unwrap();
        std::fs::write(bundle.join("Contents/Info.plist"), b"plist").unwrap();
        std::fs::write(&executable, b"binary").unwrap();
        assert_eq!(containing_app_bundle(&executable), Some(bundle));
        assert!(containing_app_bundle(temporary.path()).is_none());
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore = "changes the current user's approved Church Cap Run entry"]
    fn windows_start_at_login_round_trip() {
        assert!(
            read_windows_run_value()
                .expect("read initial Church Cap Run entry")
                .is_none(),
            "test requires no pre-existing Church Cap Run entry"
        );
        let cleanup = WindowsRunEntryCleanup;

        let enabled = set_windows_registration(true).expect("enable start at login");
        assert!(enabled.available);
        assert!(enabled.enabled);
        assert_eq!(
            read_windows_run_value().expect("read enabled Church Cap Run entry"),
            Some(windows_startup_command(
                &std::env::current_exe().expect("locate test executable")
            ))
        );

        let disabled = set_windows_registration(false).expect("disable start at login");
        assert!(disabled.available);
        assert!(!disabled.enabled);
        assert!(
            read_windows_run_value()
                .expect("read removed Church Cap Run entry")
                .is_none()
        );
        std::mem::forget(cleanup);
    }
}
