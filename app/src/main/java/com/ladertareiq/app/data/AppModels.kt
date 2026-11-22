package com.ladertareiq.app.data

data class LogEntry(
    val time: String,
    val kind: String,
    val message: String
)

data class PreparedPackageItem(
    val name: String,
    val path: String,
    val sizeBytes: Long,
    val isDirectory: Boolean,
    val isZipArchive: Boolean = false
)

data class BackupSnapshot(
    val packageName: String,
    val backupPath: String,
    val createdAt: String,
    val fileCount: Int,
    val totalBytes: Long
)

data class AppState(
    val licenseKey: String = "",
    val licenseStatus: String = "inactive",
    val licenseMessage: String = "أدخل كود التفعيل للتحقق وتجهيز الحزمة.",
    val licenseType: String = "",
    val expiresAt: String = "",
    val remainingDays: Int = 0,
    val remainingHours: Int = 0,
    val totalDays: Int = 0,
    val installedPatchVersion: String = "",
    val latestPatchVersion: String = "",
    val downloadUrl: String = "",
    val targetFileName: String = "res_pufferpatch.pak",
    val gamePackage: String = "com.tencent.ig",
    val deployMode: String = "auto",
    val patchSha256: String = "",
    val patchNotes: String = "",
    val forcePatchUpdate: Boolean = false,
    val otaVersion: String = "1.0.0",
    val otaNotes: String = "لا توجد ملاحظات OTA جديدة حالياً.",
    val latestAppVersion: String = "",
    val updateUrl: String = "",
    val updateMessage: String = "",
    val notice: String = "",
    val supportUrl: String = "https://t.me/LaderTareiqSupport",
    val maintenance: Boolean = false,
    val autoSyncOnStart: Boolean = true,
    val autoBackupBeforeDeploy: Boolean = true,
    val notificationsEnabled: Boolean = true,
    val lastPreparedPath: String = "",
    val lastDeployedTarget: String = "",
    val lastVerifiedSha256: String = "",
    val lastBackupPath: String = "",
    val lastBackupPackage: String = "",
    val logs: List<LogEntry> = emptyList()
)

data class ApiResult(
    val ok: Boolean,
    val statusCode: Int,
    val message: String,
    val rawJson: String = "",
    val fields: Map<String, String> = emptyMap()
)

data class InstallResult(
    val ok: Boolean,
    val message: String,
    val outputPath: String = "",
    val sha256: String = ""
)

enum class ShizukuStatus {
    NOT_INSTALLED,
    INSTALLED_SERVICE_STOPPED,
    PERMISSION_REQUIRED,
    READY
}
