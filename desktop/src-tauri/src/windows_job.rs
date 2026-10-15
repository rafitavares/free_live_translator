use std::mem::{size_of, zeroed};
use std::os::windows::io::AsRawHandle;
use std::process::Child;

use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
use windows_sys::Win32::System::JobObjects::{
    AssignProcessToJobObject, CreateJobObjectW, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JobObjectExtendedLimitInformation,
    SetInformationJobObject,
};

/// Owns the engine's Windows Job Object. Closing this handle (including after
/// an abrupt supervisor exit) terminates every process assigned to the job.
pub struct EngineJob(HANDLE);

unsafe impl Send for EngineJob {}

impl EngineJob {
    pub fn assign(child: &Child) -> Result<Self, String> {
        // SAFETY: A null name creates a private job and the returned handle is
        // owned by EngineJob until Drop.
        let handle = unsafe { CreateJobObjectW(std::ptr::null(), std::ptr::null()) };
        if handle.is_null() {
            return Err(std::io::Error::last_os_error().to_string());
        }
        let job = Self(handle);

        // SAFETY: The structure is initialized before Windows reads it, and
        // the byte count matches the declared information class.
        let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = unsafe { zeroed() };
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        let configured = unsafe {
            SetInformationJobObject(
                job.0,
                JobObjectExtendedLimitInformation,
                (&limits as *const JOBOBJECT_EXTENDED_LIMIT_INFORMATION).cast(),
                size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            )
        };
        if configured == 0 {
            return Err(std::io::Error::last_os_error().to_string());
        }

        // SAFETY: Child owns a live process handle and the job handle remains
        // alive for the full controller-thread lifetime.
        let assigned = unsafe { AssignProcessToJobObject(job.0, child.as_raw_handle() as HANDLE) };
        if assigned == 0 {
            return Err(std::io::Error::last_os_error().to_string());
        }
        Ok(job)
    }
}

impl Drop for EngineJob {
    fn drop(&mut self) {
        // SAFETY: EngineJob uniquely owns this non-null Windows handle.
        unsafe { CloseHandle(self.0) };
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;
    use std::thread;
    use std::time::{Duration, Instant};

    #[test]
    fn closing_the_job_terminates_the_exact_owned_process() {
        let mut child = Command::new("cmd.exe")
            .args(["/d", "/c", "ping -n 30 127.0.0.1 >nul"])
            .spawn()
            .expect("spawn long-lived test process");
        let job = EngineJob::assign(&child).expect("assign test process to kill-on-close job");
        assert!(child.try_wait().expect("query test process").is_none());

        drop(job);
        let deadline = Instant::now() + Duration::from_secs(5);
        while Instant::now() < deadline {
            if child
                .try_wait()
                .expect("query terminated process")
                .is_some()
            {
                return;
            }
            thread::sleep(Duration::from_millis(25));
        }

        let _ = child.kill();
        panic!("process remained alive after its kill-on-close Job Object was closed");
    }
}
