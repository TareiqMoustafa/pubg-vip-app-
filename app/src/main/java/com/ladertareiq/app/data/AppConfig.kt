package com.ladertareiq.app.data

object AppConfig {
    const val APP_TITLE = "Lader Tareiq"
    const val DEVELOPER_NAME = "Lader Tareiq"
    const val DEVELOPER_TAGLINE = "Smart License • OTA • Resource & Shizuku Engine"
    const val APP_VERSION = "2.4.0"
    const val OTA_VERSION = "1.0.0"

    const val SERVER_URL = "https://pak-license-server.vercel.app"
    const val DEFAULT_SUPPORT_URL = "https://t.me/LaderTareiqSupport"
    const val DEFAULT_GAME_PACKAGE = "com.tencent.ig"
    const val DEFAULT_TARGET_FILE = "res_pufferpatch.pak"
    const val DEFAULT_DEPLOY_MODE = "auto"

    const val SHIZUKU_PACKAGE = "moe.shizuku.privileged.api"
    const val SHIZUKU_PERMISSION = "moe.shizuku.permission.API_V23"

    const val CONNECT_TIMEOUT_MS = 12_000
    const val READ_TIMEOUT_MS = 35_000
    const val MAX_DOWNLOAD_BYTES: Long = 1024L * 1024L * 1024L

    val KNOWN_GAME_PACKAGES: List<Pair<String, String>> = listOf(
        "com.tencent.ig" to "PUBG Mobile (Global)",
        "com.pubg.krmobile" to "PUBG Mobile (Korea)",
        "com.vng.pubgmobile" to "PUBG Mobile (Vietnam)",
        "com.rekoo.pubgm" to "PUBG Mobile (Taiwan)",
        "com.pubg.imobile" to "BGMI (India)"
    )
}
