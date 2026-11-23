package com.ladertareiq.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

val ColorBg = Color(0xFF05070E)
val ColorBgAlt = Color(0xFF0A0F22)
val ColorCard = Color(0xFF0D142C)
val ColorCardElevated = Color(0xFF131E40)
val ColorCardBorder = Color(0xFF213366)
val ColorCyan = Color(0xFF19E3FF)
val ColorViolet = Color(0xFF8B5CFF)
val ColorPink = Color(0xFFFF2E93)
val ColorGreen = Color(0xFF38FFA2)
val ColorAmber = Color(0xFFFFB020)
val ColorText = Color(0xFFF1F5FF)
val ColorMuted = Color(0xFF93A3D1)

private val LaderDarkColors = darkColorScheme(
    primary = ColorCyan,
    onPrimary = Color(0xFF031318),
    primaryContainer = Color(0xFF0A2B36),
    onPrimaryContainer = Color(0xFFBDF5FF),
    secondary = ColorViolet,
    onSecondary = Color.White,
    secondaryContainer = Color(0xFF211442),
    onSecondaryContainer = Color(0xFFE5DBFF),
    tertiary = ColorGreen,
    onTertiary = Color(0xFF04170E),
    background = ColorBg,
    onBackground = ColorText,
    surface = ColorCard,
    onSurface = ColorText,
    surfaceVariant = ColorBgAlt,
    onSurfaceVariant = ColorMuted,
    outline = ColorCardBorder,
    error = ColorPink,
    onError = Color.White
)

private val LaderShapes = Shapes(
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(14.dp),
    large = RoundedCornerShape(20.dp)
)

@Composable
fun LaderTareiqTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LaderDarkColors,
        shapes = LaderShapes,
        content = content
    )
}
