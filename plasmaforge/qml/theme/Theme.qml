pragma Singleton
import QtQuick

QtObject {
    // Backgrounds and Surfaces
    readonly property color bg: "#131518"
    readonly property color surface: "#181b20"
    readonly property color surfaceElevated: "#1f2228"
    readonly property color card: "#22252c"
    readonly property color cardHover: "#292c34"
    readonly property color inputBg: "#17191d"

    // Subtle Borders
    readonly property color border: "#2d323c"
    readonly property color borderSubtle: "#23262e"
    readonly property color borderActive: "#14b8a6"

    // Restrained Teal Accents
    readonly property color accent: "#14b8a6"
    readonly property color accentHover: "#0d9488"
    readonly property color accentPressed: "#0f766e"
    readonly property color accentLight: "#2dd4bf"
    readonly property color accentMuted: "#134e4a"
    readonly property color accentGlow: "#14b8a626"
    readonly property color accentBorder: "#14b8a64d"

    // Text hierarchy (crisp, high readability)
    readonly property color textPrimary: "#f3f4f6"
    readonly property color textSecondary: "#9ca3af"
    readonly property color textMuted: "#6b7280"
    readonly property color textOnAccent: "#042f2e"

    // Feedback status
    readonly property color success: "#10b981"
    readonly property color successMuted: "#064e3b"
    readonly property color warning: "#f59e0b"
    readonly property color warningMuted: "#78350f"
    readonly property color danger: "#ef4444"
    readonly property color dangerMuted: "#7f1d1d"
    readonly property color info: "#38bdf8"
    readonly property color infoMuted: "#0c4a6e"

    // Spacing
    readonly property int spaceXs: 4
    readonly property int spaceSm: 8
    readonly property int spaceMd: 12
    readonly property int spaceLg: 16
    readonly property int spaceXl: 20
    readonly property int spaceXxl: 24
    readonly property int spaceXxxl: 32

    // Border Radii
    readonly property int radiusSm: 4
    readonly property int radiusMd: 6
    readonly property int radiusLg: 8
    readonly property int radiusXl: 12
    readonly property int radiusFull: 9999

    // Font Families & Sizes
    readonly property string fontFamily: "Inter, Noto Sans, Cantarell, Sans Serif"
    readonly property string fontMono: "JetBrains Mono, Hack, Monospace"

    readonly property int fontSizeXs: 10
    readonly property int fontSizeSm: 11
    readonly property int fontSizeBase: 13
    readonly property int fontSizeMd: 14
    readonly property int fontSizeLg: 16
    readonly property int fontSizeXl: 18
    readonly property int fontSizeTitle: 22

    // Transitions
    readonly property int animDurationFast: 120
    readonly property int animDurationNormal: 200
}
