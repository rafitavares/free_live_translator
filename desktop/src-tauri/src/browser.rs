use serde::Deserialize;
use tauri::{AppHandle, Manager};
use tauri_plugin_opener::OpenerExt;

use crate::lifecycle::EngineSupervisor;
use crate::model::SupervisorPhase;

#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ChurchCapRoute {
    Operator,
    Viewer,
    Display,
    Obs,
}

pub fn open_route_internal(app: &AppHandle, route: ChurchCapRoute) -> Result<(), String> {
    let supervisor = app.state::<EngineSupervisor>();
    let status = supervisor.snapshot();
    if !matches!(
        status.phase,
        SupervisorPhase::Ready | SupervisorPhase::CaptionsLive
    ) {
        return Err("Church Cap must be ready before opening the browser.".into());
    }

    let viewer_base = status.viewer_url.trim_end_matches('/');
    let url = match route {
        ChurchCapRoute::Operator => status.operator_url,
        ChurchCapRoute::Viewer => format!("{viewer_base}/"),
        ChurchCapRoute::Display => format!("{viewer_base}/display"),
        ChurchCapRoute::Obs => format!("{viewer_base}/obs"),
    };
    app.opener()
        .open_url(url, None::<&str>)
        .map_err(|error| error.to_string())
}

#[tauri::command]
pub fn open_church_cap_route(app: AppHandle, route: ChurchCapRoute) -> Result<(), String> {
    open_route_internal(&app, route)
}
