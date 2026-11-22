package com.ladertareiq.app.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

class StateStore(context: Context) {
    private val appContext = context.applicationContext
    private val prefs = appContext.getSharedPreferences("lader_tareiq_prefs", Context.MODE_PRIVATE)
    private val stateFile: File by lazy {
        val dir = File(appContext.filesDir, "lader_tareiq_state").apply { mkdirs() }
        File(dir, "state.json")
    }

    fun getDeviceId(): String {
        val existing = prefs.getString("device_id", null)
        if (!existing.isNullOrBlank()) return existing
        val androidId = try {
            android.provider.Settings.Secure.getString(
                appContext.contentResolver,
                android.provider.Settings.Secure.ANDROID_ID
            )
        } catch (_: Exception) {
            null
        }
        val cleanBase = androidId?.replace(Regex("[^A-Za-z0-9_-]"), "")?.take(24).orEmpty()
        val generated = if (cleanBase.length >= 6) "LT-${cleanBase.uppercase(Locale.US)}" else {
            "LT-${java.util.UUID.randomUUID().toString().replace("-", "").take(16).uppercase(Locale.US)}"
        }
        prefs.edit().putString("device_id", generated).apply()
        return generated
    }

    fun load(): AppState {
        if (!stateFile.exists()) return AppState()
        return try {
            val raw = stateFile.readText(Charsets.UTF_8)
            val obj = JSONObject(raw)
            val logsArr = obj.optJSONArray("logs") ?: JSONArray()
            val parsedLogs = mutableListOf<LogEntry>()
            for (i in 0 until logsArr.length()) {
                val item = logsArr.optJSONObject(i) ?: continue
                parsedLogs.add(
                    LogEntry(
                        time = item.optString("time", ""),
                        kind = item.optString("kind", "info"),
                        message = item.optString("message", "")
                    )
                )
            }
            AppState(
                licenseKey = obj.optString("license_key", ""),
                licenseStatus = obj.optString("license_status", "inactive"),
                licenseMessage = obj.optString("license_message", "أدخل كود التفعيل للتحقق وتجهيز الحزمة."),
                licenseType = obj.optString("license_type", ""),
                expiresAt = obj.optString("expires_at", ""),
                remainingDays = obj.optInt("remaining_days", 0),
                remainingHours = obj.optInt("remaining_hours", 0),
                totalDays = obj.optInt("total_days", 0),
                installedPatchVersion = obj.optString("installed_patch_version", ""),
                latestPatchVersion = obj.optString("latest_patch_version", ""),
                downloadUrl = obj.optString("download_url", ""),
                targetFileName = obj.optString("target_file_name", AppConfig.DEFAULT_TARGET_FILE),
                gamePackage = obj.optString("game_package", AppConfig.DEFAULT_GAME_PACKAGE),
                deployMode = obj.optString("deploy_mode", AppConfig.DEFAULT_DEPLOY_MODE),
                patchSha256 = obj.optString("patch_sha256", ""),
                patchNotes = obj.optString("patch_notes", ""),
                forcePatchUpdate = obj.optBoolean("force_patch_update", false),
                otaVersion = obj.optString("ota_version", AppConfig.OTA_VERSION),
                otaNotes = obj.optString("ota_notes", "لا توجد ملاحظات OTA جديدة حالياً."),
                latestAppVersion = obj.optString("latest_app_version", ""),
                updateUrl = obj.optString("update_url", ""),
                updateMessage = obj.optString("update_message", ""),
                notice = obj.optString("notice", ""),
                supportUrl = obj.optString("support_url", AppConfig.DEFAULT_SUPPORT_URL),
                maintenance = obj.optBoolean("maintenance", false),
                autoSyncOnStart = obj.optBoolean("auto_sync_on_start", true),
                autoBackupBeforeDeploy = obj.optBoolean("auto_backup_before_deploy", true),
                notificationsEnabled = obj.optBoolean("notifications_enabled", true),
                lastPreparedPath = obj.optString("last_prepared_path", ""),
                lastDeployedTarget = obj.optString("last_deployed_target", ""),
                lastVerifiedSha256 = obj.optString("last_verified_sha256", ""),
                lastBackupPath = obj.optString("last_backup_path", ""),
                lastBackupPackage = obj.optString("last_backup_package", ""),
                logs = parsedLogs
            )
        } catch (_: Exception) {
            AppState()
        }
    }

    fun save(transform: (AppState) -> AppState): AppState {
        synchronized(this) {
            val updated = transform(load())
            try {
                val obj = JSONObject().apply {
                    put("license_key", updated.licenseKey)
                    put("license_status", updated.licenseStatus)
                    put("license_message", updated.licenseMessage)
                    put("license_type", updated.licenseType)
                    put("expires_at", updated.expiresAt)
                    put("remaining_days", updated.remainingDays)
                    put("remaining_hours", updated.remainingHours)
                    put("total_days", updated.totalDays)
                    put("installed_patch_version", updated.installedPatchVersion)
                    put("latest_patch_version", updated.latestPatchVersion)
                    put("download_url", updated.downloadUrl)
                    put("target_file_name", updated.targetFileName)
                    put("game_package", updated.gamePackage)
                    put("deploy_mode", updated.deployMode)
                    put("patch_sha256", updated.patchSha256)
                    put("patch_notes", updated.patchNotes)
                    put("force_patch_update", updated.forcePatchUpdate)
                    put("ota_version", updated.otaVersion)
                    put("ota_notes", updated.otaNotes)
                    put("latest_app_version", updated.latestAppVersion)
                    put("update_url", updated.updateUrl)
                    put("update_message", updated.updateMessage)
                    put("notice", updated.notice)
                    put("support_url", updated.supportUrl)
                    put("maintenance", updated.maintenance)
                    put("auto_sync_on_start", updated.autoSyncOnStart)
                    put("auto_backup_before_deploy", updated.autoBackupBeforeDeploy)
                    put("notifications_enabled", updated.notificationsEnabled)
                    put("last_prepared_path", updated.lastPreparedPath)
                    put("last_deployed_target", updated.lastDeployedTarget)
                    put("last_verified_sha256", updated.lastVerifiedSha256)
                    put("last_backup_path", updated.lastBackupPath)
                    put("last_backup_package", updated.lastBackupPackage)

                    val arr = JSONArray()
                    for (entry in updated.logs.takeLast(200)) {
                        arr.put(
                            JSONObject().apply {
                                put("time", entry.time)
                                put("kind", entry.kind)
                                put("message", entry.message)
                            }
                        )
                    }
                    put("logs", arr)
                }
                val tmp = File(stateFile.parentFile, "state.json.tmp")
                tmp.writeText(obj.toString(2), Charsets.UTF_8)
                if (!tmp.renameTo(stateFile)) {
                    stateFile.writeText(obj.toString(2), Charsets.UTF_8)
                    tmp.delete()
                }
            } catch (_: Exception) {
            }
            return updated
        }
    }

    fun addLog(kind: String, message: String): AppState {
        val current = load()
        if (!current.notificationsEnabled && kind.lowercase(Locale.ROOT) != "error") {
            return current
        }
        val fmt = SimpleDateFormat("yyyy-MM-dd HH:mm:ss 'UTC'", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
        val entry = LogEntry(
            time = fmt.format(Date()),
            kind = kind.lowercase(Locale.ROOT),
            message = message.trim()
        )
        return save { st ->
            st.copy(logs = (st.logs + entry).takeLast(200))
        }
    }

    fun clearLogs(): AppState = save { it.copy(logs = emptyList()) }
}
