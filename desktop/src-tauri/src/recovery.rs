use std::fs;
use std::io::ErrorKind;
use std::path::{Path, PathBuf};

const AUTH_DATA_DIRECTORY: &str = "data";
const AUTH_BACKUP_FILE: &str = "operator_auth.backup.json";
const AUTH_PRIMARY_FILE: &str = "operator_auth.json";

fn operator_auth_paths(app_data_dir: &Path) -> [PathBuf; 2] {
    let auth_data_dir = app_data_dir.join(AUTH_DATA_DIRECTORY);
    [
        auth_data_dir.join(AUTH_BACKUP_FILE),
        auth_data_dir.join(AUTH_PRIMARY_FILE),
    ]
}

pub fn reset_operator_auth(app_data_dir: &Path) -> Result<usize, String> {
    let mut removed = 0;
    // Remove the backup first. If that fails, the primary password remains
    // untouched and Church Cap can restart without leaving a partial reset.
    for path in operator_auth_paths(app_data_dir) {
        match fs::symlink_metadata(&path) {
            Ok(metadata) if metadata.file_type().is_file() || metadata.file_type().is_symlink() => {
                fs::remove_file(&path).map_err(|error| {
                    format!(
                        "Church Cap could not remove its stored operator authentication: {error}"
                    )
                })?;
                removed += 1;
            }
            Ok(_) => {
                return Err(
                    "Church Cap found an unexpected item in its authentication storage and left it unchanged."
                        .into(),
                );
            }
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(error) => {
                return Err(format!(
                    "Church Cap could not inspect its stored operator authentication: {error}"
                ));
            }
        }
    }
    Ok(removed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temporary_data_dir(test_name: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should follow the Unix epoch")
            .as_nanos();
        std::env::temp_dir().join(format!(
            "church-cap-{test_name}-{}-{nonce}",
            std::process::id()
        ))
    }

    #[test]
    fn reset_removes_only_the_known_primary_and_backup_files() {
        let root = temporary_data_dir("password-reset");
        let data = root.join(AUTH_DATA_DIRECTORY);
        fs::create_dir_all(&data).unwrap();
        let [backup, primary] = operator_auth_paths(&root);
        fs::write(&backup, "backup").unwrap();
        fs::write(&primary, "primary").unwrap();
        let unrelated = data.join("runtime.json");
        fs::write(&unrelated, "keep").unwrap();

        assert_eq!(reset_operator_auth(&root).unwrap(), 2);
        assert!(!backup.exists());
        assert!(!primary.exists());
        assert_eq!(fs::read_to_string(&unrelated).unwrap(), "keep");

        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn reset_is_idempotent_when_no_password_has_been_stored() {
        let root = temporary_data_dir("empty-password-reset");
        assert_eq!(reset_operator_auth(&root).unwrap(), 0);
    }
}
