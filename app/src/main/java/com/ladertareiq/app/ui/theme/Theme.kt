package com.ladertareiq.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val ColorBg = Color(0xFF05070E)
val ColorBgAlt = Color(0xFF0A0F22)
val ColorCard = Color(0xFF0D142C)
val ColorCardElevated = Color(0xFF121C3D)
val ColorCardBorder = Color(0xFF1F2F5E)
val ColorCyan = Color(0xFF19E3FF)
val ColorViolet = Color(0xFF8B5CFF)
val ColorPink = Color(0xFFFF2E93)
val ColorGreen = Color(0xFF38FFA2)
val ColorAmber = Color(0xFFFFB020)
val ColorText = Color(0xFFF1F5FF)
val ColorMuted = Color(0xFF8E9CC7)

private val LaderDarkColors = darkColorScheme(
    primary = ColorCyan,
    onPrimary = Color(0xFF031318),
    secondary = ColorViolet,
    onSecondary = Color.White,
    tertiary = ColorGreen,
    background = ColorBg,
    onBackground = ColorText,
    surface = ColorCard,
    onSurface = ColorText,
    surfaceVariant = ColorBgAlt,
    onSurfaceVariant = ColorMuted,
    error = ColorPink,
    onError = Color.White
)

@Composable
fun LaderTareiqTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LaderDarkColors,
        content = content
    )
}
