#!/usr/bin/env swift

import AppKit
import Foundation

private let canvasSize = 1024

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

guard CommandLine.arguments.count == 3 else {
    fail("usage: generate-desktop-app-icon.swift INPUT_LOGO.png OUTPUT_ICON.png")
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])

guard let sourceImage = NSImage(contentsOf: inputURL) else {
    fail("could not read \(inputURL.path)")
}

func rasterize(_ image: NSImage, width: Int, height: Int) -> NSBitmapImageRep {
    guard let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: width,
        pixelsHigh: height,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bitmapFormat: [],
        bytesPerRow: 0,
        bitsPerPixel: 0
    ) else {
        fail("could not allocate the icon bitmap")
    }

    bitmap.size = NSSize(width: width, height: height)
    guard let context = NSGraphicsContext(bitmapImageRep: bitmap) else {
        fail("could not create the icon drawing context")
    }

    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = context
    NSColor.clear.setFill()
    NSRect(x: 0, y: 0, width: width, height: height).fill()
    image.draw(
        in: NSRect(x: 0, y: 0, width: width, height: height),
        from: .zero,
        operation: .copy,
        fraction: 1,
        respectFlipped: false,
        hints: [.interpolation: NSImageInterpolation.high]
    )
    context.flushGraphics()
    NSGraphicsContext.restoreGraphicsState()
    return bitmap
}

func opaqueBounds(in bitmap: NSBitmapImageRep) -> NSRect {
    var minX = bitmap.pixelsWide
    var minY = bitmap.pixelsHigh
    var maxX = -1
    var maxY = -1

    for y in 0..<bitmap.pixelsHigh {
        for x in 0..<bitmap.pixelsWide where (bitmap.colorAt(x: x, y: y)?.alphaComponent ?? 0) > 0.02 {
            minX = min(minX, x)
            minY = min(minY, y)
            maxX = max(maxX, x)
            maxY = max(maxY, y)
        }
    }

    guard maxX >= minX, maxY >= minY else {
        fail("the input logo has no visible pixels")
    }

    return NSRect(x: minX, y: minY, width: maxX - minX + 1, height: maxY - minY + 1)
}

let sourceWidth = max(Int(sourceImage.size.width.rounded()), 1)
let sourceHeight = max(Int(sourceImage.size.height.rounded()), 1)
let sourceBitmap = rasterize(sourceImage, width: sourceWidth, height: sourceHeight)
let sourceBounds = opaqueBounds(in: sourceBitmap)
// NSBitmapImageRep reports pixel rows from the image's top edge, while
// NSImage's source rectangle uses AppKit's bottom-left drawing coordinates.
// Convert the vertical origin so the cross at the top of the mark is retained.
let sourceDrawBounds = NSRect(
    x: sourceBounds.minX,
    y: CGFloat(sourceHeight) - sourceBounds.maxY,
    width: sourceBounds.width,
    height: sourceBounds.height
)

guard let output = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: canvasSize,
    pixelsHigh: canvasSize,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bitmapFormat: [],
    bytesPerRow: 0,
    bitsPerPixel: 0
) else {
    fail("could not allocate the output icon")
}

output.size = NSSize(width: canvasSize, height: canvasSize)
guard let graphics = NSGraphicsContext(bitmapImageRep: output) else {
    fail("could not create the output drawing context")
}

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = graphics
let cg = graphics.cgContext
cg.clear(CGRect(x: 0, y: 0, width: canvasSize, height: canvasSize))

let tileRect = NSRect(x: 62, y: 70, width: 900, height: 900)
let tile = NSBezierPath(roundedRect: tileRect, xRadius: 218, yRadius: 218)

// A restrained floating shadow keeps the white tile legible on both light and
// dark desktops without turning the icon into a heavy raised button.
cg.saveGState()
cg.setShadow(
    offset: CGSize(width: 0, height: -24),
    blur: 42,
    color: NSColor(calibratedWhite: 0.03, alpha: 0.26).cgColor
)
NSColor(calibratedWhite: 0.98, alpha: 0.99).setFill()
tile.fill()
cg.restoreGState()

let glass = NSGradient(colorsAndLocations:
    (NSColor(calibratedRed: 1.00, green: 1.00, blue: 1.00, alpha: 1.00), 0.0),
    (NSColor(calibratedRed: 0.975, green: 0.982, blue: 1.00, alpha: 1.00), 0.55),
    (NSColor(calibratedRed: 0.91, green: 0.925, blue: 0.965, alpha: 1.00), 1.0)
)!
glass.draw(in: tile, angle: -90)

// Soft cool reflections give the tile a glass character while the centre
// remains clean behind the brand mark.
cg.saveGState()
tile.addClip()
let colourSpace = CGColorSpaceCreateDeviceRGB()
let violet = CGGradient(
    colorsSpace: colourSpace,
    colors: [
        NSColor(calibratedRed: 0.38, green: 0.22, blue: 0.93, alpha: 0.16).cgColor,
        NSColor(calibratedRed: 0.38, green: 0.22, blue: 0.93, alpha: 0.0).cgColor,
    ] as CFArray,
    locations: [0, 1]
)!
cg.drawRadialGradient(
    violet,
    startCenter: CGPoint(x: 850, y: 180),
    startRadius: 0,
    endCenter: CGPoint(x: 850, y: 180),
    endRadius: 470,
    options: [.drawsAfterEndLocation]
)
let cyan = CGGradient(
    colorsSpace: colourSpace,
    colors: [
        NSColor(calibratedRed: 0.20, green: 0.72, blue: 0.96, alpha: 0.13).cgColor,
        NSColor(calibratedRed: 0.20, green: 0.72, blue: 0.96, alpha: 0.0).cgColor,
    ] as CFArray,
    locations: [0, 1]
)!
cg.drawRadialGradient(
    cyan,
    startCenter: CGPoint(x: 190, y: 850),
    startRadius: 0,
    endCenter: CGPoint(x: 190, y: 850),
    endRadius: 450,
    options: [.drawsAfterEndLocation]
)
cg.restoreGState()

NSColor(calibratedWhite: 1.0, alpha: 0.88).setStroke()
tile.lineWidth = 5
tile.stroke()
let innerTile = NSBezierPath(roundedRect: tileRect.insetBy(dx: 7, dy: 7), xRadius: 211, yRadius: 211)
NSColor(calibratedRed: 0.28, green: 0.34, blue: 0.52, alpha: 0.10).setStroke()
innerTile.lineWidth = 2
innerTile.stroke()

// Crop away the transparent padding in the canonical brand asset before
// fitting it, making the exact logo materially larger at Dock size.
let maximumLogo = NSSize(width: 520, height: 620)
let logoScale = min(maximumLogo.width / sourceBounds.width, maximumLogo.height / sourceBounds.height)
let logoSize = NSSize(width: sourceBounds.width * logoScale, height: sourceBounds.height * logoScale)
let logoRect = NSRect(
    x: (CGFloat(canvasSize) - logoSize.width) / 2,
    y: (CGFloat(canvasSize) - logoSize.height) / 2 + 6,
    width: logoSize.width,
    height: logoSize.height
)

let sourceRaster = NSImage(size: NSSize(width: sourceWidth, height: sourceHeight))
sourceRaster.addRepresentation(sourceBitmap)
sourceRaster.draw(
    in: logoRect,
    from: sourceDrawBounds,
    operation: .sourceOver,
    fraction: 1,
    respectFlipped: false,
    hints: [.interpolation: NSImageInterpolation.high]
)

graphics.flushGraphics()
NSGraphicsContext.restoreGraphicsState()

guard let png = output.representation(using: .png, properties: [:]) else {
    fail("could not encode the output PNG")
}

do {
    try FileManager.default.createDirectory(
        at: outputURL.deletingLastPathComponent(),
        withIntermediateDirectories: true
    )
    try png.write(to: outputURL, options: .atomic)
    print("created: \(outputURL.path)")
} catch {
    fail("could not write \(outputURL.path): \(error.localizedDescription)")
}
