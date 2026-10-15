$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$SourceIcon = Join-Path $ProjectRoot "assets\branding\church-cap-app-icon-white-glass.png"
$SourceSidebarBackground = Join-Path $ProjectRoot "assets\branding\church-cap-installer-sidebar-background.png"
$OutputDir = Join-Path $ProjectRoot "desktop\src-tauri\installer\windows"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function New-Canvas([int]$Width, [int]$Height) {
    return [System.Drawing.Bitmap]::new(
        $Width,
        $Height,
        [System.Drawing.Imaging.PixelFormat]::Format24bppRgb
    )
}

$Icon = [System.Drawing.Image]::FromFile($SourceIcon)
$SidebarBackground = [System.Drawing.Image]::FromFile($SourceSidebarBackground)
try {
    # NSIS recommends a 150x57 logical header and a 164x314 logical sidebar.
    # Render at 3x and let Modern UI scale them to the current DPI so the
    # artwork remains crisp on high-density Windows displays.
    $Header = New-Canvas 450 171
    try {
        $Graphics = [System.Drawing.Graphics]::FromImage($Header)
        try {
            $Graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $Graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $Graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
            $Graphics.Clear([System.Drawing.Color]::White)
            $Graphics.DrawImage($Icon, [System.Drawing.Rectangle]::new(18, 18, 135, 135))
            $BrandFont = [System.Drawing.Font]::new("Segoe UI Semibold", 39, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
            $TagFont = [System.Drawing.Font]::new("Segoe UI", 24, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
            try {
                $Graphics.DrawString("Church Cap", $BrandFont, [System.Drawing.Brushes]::MidnightBlue, 159, 36)
                $Graphics.DrawString("Local live captions", $TagFont, [System.Drawing.Brushes]::SlateGray, 162, 93)
            }
            finally {
                $BrandFont.Dispose()
                $TagFont.Dispose()
            }
        }
        finally {
            $Graphics.Dispose()
        }
        $Header.Save((Join-Path $OutputDir "header.bmp"), [System.Drawing.Imaging.ImageFormat]::Bmp)
    }
    finally {
        $Header.Dispose()
    }

    $Sidebar = New-Canvas 492 942
    try {
        $Graphics = [System.Drawing.Graphics]::FromImage($Sidebar)
        try {
            $Graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $Graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $Graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
            $Area = [System.Drawing.Rectangle]::new(0, 0, 492, 942)
            $Graphics.DrawImage($SidebarBackground, $Area)
            $Graphics.DrawImage($Icon, [System.Drawing.Rectangle]::new(69, 102, 354, 354))
            $BrandFont = [System.Drawing.Font]::new("Segoe UI Semibold", 60, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
            $CopyFont = [System.Drawing.Font]::new("Segoe UI", 30, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
            $Centered = [System.Drawing.StringFormat]::new()
            try {
                $Centered.Alignment = [System.Drawing.StringAlignment]::Center
                $Graphics.DrawString("Church Cap", $BrandFont, [System.Drawing.Brushes]::White, [System.Drawing.RectangleF]::new(24, 528, 444, 90), $Centered)
                $Graphics.DrawString("Live captions.`nLocal and private.", $CopyFont, [System.Drawing.Brushes]::WhiteSmoke, [System.Drawing.RectangleF]::new(36, 657, 420, 135), $Centered)
            }
            finally {
                $Centered.Dispose()
                $BrandFont.Dispose()
                $CopyFont.Dispose()
            }
        }
        finally {
            $Graphics.Dispose()
        }
        $Sidebar.Save((Join-Path $OutputDir "sidebar.bmp"), [System.Drawing.Imaging.ImageFormat]::Bmp)
    }
    finally {
        $Sidebar.Dispose()
    }
}
finally {
    $SidebarBackground.Dispose()
    $Icon.Dispose()
}

Write-Host "Generated Church Cap NSIS branding in $OutputDir"
