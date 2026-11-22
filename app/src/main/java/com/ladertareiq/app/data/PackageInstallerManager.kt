package com.ladertareiq.app.data

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.StatFs
import android.provider.Settings
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.BufferedInputStream
import java.io.BufferedReader
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.zip.ZipInputStream

object PackageInstallerManager {
    fun isNetworkConnected(context: Context): Boolean {
        return try {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val net = cm.activeNetwork ?: return false
            val caps = cm.getNetworkCapabilities(net) ?: return false
            caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
        } catch (_: Exception) {
            false
        }
    }

    fun getAvailableStorageBytes(context: Context): Long {
        return try {
            val dir = getTargetPackagesDir(context)
            val stat = StatFs(dir.absolutePath)
            stat.availableBlocksLong * stat.blockSizeLong
        } catch (_: Exception) {
            0L
        }
    }

    fun hasStoragePermissions(context: Context): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (Environment.isExternalStorageManager()) return true
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val imgOk = ContextCompat.checkSelfPermission(
                context,
                android.Manifest.permission.READ_MEDIA_IMAGES
            ) == PackageManager.PERMISSION_GRANTED
            val vidOk = ContextCompat.checkSelfPermission(
                context,
                android.Manifest.permission.READ_MEDIA_VIDEO
            ) == PackageManager.PERMISSION_GRANTED
            val audOk = ContextCompat.checkSelfPermission(
                context,
                android.Manifest.permission.READ_MEDIA_AUDIO
            ) == PackageManager.PERMISSION_GRANTED
            return imgOk || vidOk || audOk
        }
        val readOk = ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.READ_EXTERNAL_STORAGE
        ) == PackageManager.PERMISSION_GRANTED
        val writeOk = ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.WRITE_EXTERNAL_STORAGE
        ) == PackageManager.PERMISSION_GRANTED
        return readOk && writeOk
    }

    fun openManageStorageSettings(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            try {
                val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                    data = Uri.parse("package:${context.packageName}")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
                return
            } catch (_: Exception) {
            }
        }
        val fallback = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.parse("package:${context.packageName}")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(fallback)
    }

    fun inspectShizuku(context: Context): ShizukuStatus {
        val installed = try {
            context.packageManager.getPackageInfo(AppConfig.SHIZUKU_PACKAGE, 0)
            true
        } catch (_: Exception) {
            false
        }
        if (!installed) return ShizukuStatus.NOT_INSTALLED

        val granted = try {
            ContextCompat.checkSelfPermission(
                context,
                AppConfig.SHIZUKU_PERMISSION
            ) == PackageManager.PERMISSION_GRANTED
        } catch (_: Exception) {
            false
        }
        if (granted) return ShizukuStatus.READY

        val binderAlive = try {
            val clazz = Class.forName("rikka.shizuku.Shizuku")
            val pingMethod = clazz.getMethod("pingBinder")
            (pingMethod.invoke(null) as? Boolean) == true
        } catch (_: Exception) {
            false
        }
        return if (binderAlive) ShizukuStatus.PERMISSION_REQUIRED else ShizukuStatus.INSTALLED_SERVICE_STOPPED
    }

    fun openShizukuApp(context: Context) {
        val launchIntent = context.packageManager.getLaunchIntentForPackage(AppConfig.SHIZUKU_PACKAGE)
        if (launchIntent != null) {
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(launchIntent)
        } else {
            openManageStorageSettings(context)
        }
    }

    fun isPackageInstalled(context: Context, packageName: String): Boolean {
        val clean = packageName.trim()
        if (clean.isEmpty()) return false
        return try {
            context.packageManager.getPackageInfo(clean, 0)
            true
        } catch (_: Exception) {
            false
        }
    }

    fun launchTargetGame(context: Context, packageName: String): InstallResult {
        val clean = packageName.trim()
        if (clean.isEmpty()) return InstallResult(false, "اسم حزمة اللعبة فارغ.")
        val intent = context.packageManager.getLaunchIntentForPackage(clean)
            ?: return InstallResult(false, "التطبيق أو اللعبة ($clean) غير مثبّتة على الجهاز.")
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
        return InstallResult(true, "تم تشغيل $clean بنجاح.")
    }

    fun getTargetPackagesDir(context: Context): File {
        val baseDir = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && Environment.isExternalStorageManager()) {
            File(Environment.getExternalStorageDirectory(), "LaderTareiq/Packages")
        } else {
            File(context.getExternalFilesDir(null) ?: context.filesDir, "LaderTareiq/Packages")
        }
        baseDir.mkdirs()
        return baseDir
    }

    fun getBackupsRootDir(context: Context): File {
        val baseDir = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && Environment.isExternalStorageManager()) {
            File(Environment.getExternalStorageDirectory(), "LaderTareiq/Backups")
        } else {
            File(context.getExternalFilesDir(null) ?: context.filesDir, "LaderTareiq/Backups")
        }
        baseDir.mkdirs()
        return baseDir
    }

    fun getGameAndroidDataTargetDir(gamePackage: String): File {
        val cleanPkg = gamePackage.trim().ifBlank { AppConfig.DEFAULT_GAME_PACKAGE }
        return File(Environment.getExternalStorageDirectory(), "Android/data/$cleanPkg/files/UE4Game/ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks")
    }

    fun listPreparedItems(context: Context): List<PreparedPackageItem> {
        val dir = getTargetPackagesDir(context)
        val entries = dir.listFiles() ?: return emptyList()
        return entries
            .filter { !it.name.endsWith(".part") }
            .sortedByDescending { it.lastModified() }
            .map { f ->
                val sz = if (f.isDirectory) {
                    f.walkTopDown().filter { it.isFile }.sumOf { it.length() }
                } else {
                    f.length()
                }
                PreparedPackageItem(
                    name = f.name,
                    path = f.absolutePath,
                    sizeBytes = sz,
                    isDirectory = f.isDirectory,
                    isZipArchive = !f.isDirectory && f.extension.lowercase(Locale.US) == "zip"
                )
            }
    }

    fun clearPreparedPackages(context: Context): Int {
        val dir = getTargetPackagesDir(context)
        val files = dir.listFiles() ?: return 0
        var count = 0
        for (f in files) {
            try {
                if (f.deleteRecursively()) count++
            } catch (_: Exception) {
            }
        }
        return count
    }

    fun formatBytes(bytes: Long): String {
        if (bytes <= 0L) return "0 B"
        val kb = bytes / 1024.0
        if (kb < 1024.0) return String.format(Locale.US, "%.1f KB", kb)
        val mb = kb / 1024.0
        if (mb < 1024.0) return String.format(Locale.US, "%.2f MB", mb)
        val gb = mb / 1024.0
        return String.format(Locale.US, "%.2f GB", gb)
    }

    fun computeSha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { fis ->
            val buf = ByteArray(65536)
            var read = fis.read(buf)
            while (read > 0) {
                digest.update(buf, 0, read)
                read = fis.read(buf)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }.lowercase(Locale.US)
    }

    suspend fun verifyLocalItemSha256(path: String, expectedSha: String): InstallResult = withContext(Dispatchers.IO) {
        val f = File(path.trim())
        if (!f.exists() || f.isDirectory) {
            return@withContext InstallResult(false, "اختر ملفاً فردياً لفحص بصمة SHA-256.")
        }
        val actual = computeSha256(f)
        val exp = expectedSha.trim().lowercase(Locale.US)
        if (exp.isNotEmpty() && actual != exp) {
            return@withContext InstallResult(false, "عدم تطابق SHA-256 للملف ${f.name}.", f.absolutePath, actual)
        }
        val statusMsg = if (exp.isNotEmpty()) {
            "تم التحقق من تطابق SHA-256 لـ ${f.name}"
        } else {
            "بصمة SHA-256 لـ ${f.name}: ${actual.take(16)}..."
        }
        InstallResult(true, statusMsg, f.absolutePath, actual)
    }

    suspend fun extractZipLocally(context: Context, zipPath: String): InstallResult = withContext(Dispatchers.IO) {
        val zipFile = File(zipPath.trim())
        if (!zipFile.exists() || zipFile.isDirectory) {
            return@withContext InstallResult(false, "ملف الأرشيف غير موجود.")
        }
        val outDir = getTargetPackagesDir(context)
        val extractDir = File(outDir, "${zipFile.nameWithoutExtension}_extracted")
        if (extractDir.exists()) extractDir.deleteRecursively()
        extractDir.mkdirs()
        val canonicalRoot = extractDir.canonicalPath + File.separator

        return@withContext try {
            ZipInputStream(BufferedInputStream(FileInputStream(zipFile))).use { zis ->
                var entry = zis.nextEntry
                while (entry != null) {
                    val outFile = File(extractDir, entry.name)
                    if (!outFile.canonicalPath.startsWith(canonicalRoot)) {
                        extractDir.deleteRecursively()
                        return@withContext InstallResult(false, "تم رفض أرشيف يحتوي على مسارات غير آمنة.")
                    }
                    if (entry.isDirectory) {
                        outFile.mkdirs()
                    } else {
                        outFile.parentFile?.mkdirs()
                        FileOutputStream(outFile).use { fos ->
                            val buf = ByteArray(32768)
                            var len = zis.read(buf)
                            while (len > 0) {
                                fos.write(buf, 0, len)
                                len = zis.read(buf)
                            }
                        }
                    }
                    zis.closeEntry()
                    entry = zis.nextEntry
                }
            }
            InstallResult(true, "تم فك الضغط في: ${extractDir.absolutePath}", extractDir.absolutePath)
        } catch (ex: Exception) {
            extractDir.deleteRecursively()
            InstallResult(false, "تعذر فك ضغط الأرشيف: ${ex.localizedMessage ?: ex.javaClass.simpleName}")
        }
    }

    private suspend fun executeShizukuCommand(command: String): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        try {
            val clazz = Class.forName("rikka.shizuku.Shizuku")
            val newProc = clazz.getDeclaredMethod(
                "newProcess",
                Array<String>::class.java,
                Array<String>::class.java,
                String::class.java
            )
            newProc.isAccessible = true
            val proc = newProc.invoke(null, arrayOf("sh", "-c", command), null, null) as? Process
                ?: return@withContext false to "تعذر إنشاء عملية عبر Shizuku."

            val out = BufferedReader(InputStreamReader(proc.inputStream)).use { it.readText() }
            val err = BufferedReader(InputStreamReader(proc.errorStream)).use { it.readText() }
            val exitCode = proc.waitFor()
            if (exitCode == 0) {
                true to out.trim().ifBlank { "تم تنفيذ الأمر عبر Shizuku بنجاح." }
            } else {
                false to (err.trim().ifBlank { "فشل أمر Shizuku برمز $exitCode" })
            }
        } catch (_: Exception) {
            false to "واجهة Shizuku البرمجية غير مفعّلة في هذا البناء (استخدم النقل المباشر أو أداة Shizuku)."
        }
    }

    suspend fun backupTargetPaks(context: Context, gamePackage: String): InstallResult = withContext(Dispatchers.IO) {
        val cleanPkg = gamePackage.trim().ifBlank { AppConfig.DEFAULT_GAME_PACKAGE }
        val targetDir = getGameAndroidDataTargetDir(cleanPkg)
        if (!targetDir.exists() || !targetDir.isDirectory) {
            return@withContext InstallResult(false, "مجلد Paks غير موجود لـ $cleanPkg.")
        }
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val backupDir = File(getBackupsRootDir(context), "${cleanPkg}_$stamp")
        return@withContext try {
            targetDir.copyRecursively(backupDir, overwrite = true)
            val count = backupDir.walkTopDown().filter { it.isFile }.count()
            InstallResult(
                true,
                "تم أخذ نسخة احتياطية ($count ملف) لـ $cleanPkg.",
                backupDir.absolutePath
            )
        } catch (ex: Exception) {
            InstallResult(false, "تعذر إنشاء النسخة الاحتياطية: ${ex.localizedMessage ?: ex.javaClass.simpleName}")
        }
    }

    suspend fun restoreTargetPaks(context: Context, backupPath: String, gamePackage: String): InstallResult =
        withContext(Dispatchers.IO) {
            val src = File(backupPath.trim())
            if (!src.exists() || !src.isDirectory) {
                return@withContext InstallResult(false, "النسخة الاحتياطية المحددة غير موجودة.")
            }
            val targetDir = getGameAndroidDataTargetDir(gamePackage)
            return@withContext try {
                targetDir.mkdirs()
                src.copyRecursively(targetDir, overwrite = true)
                InstallResult(
                    true,
                    "تمت استعادة النسخة الاحتياطية إلى ${targetDir.absolutePath}.",
                    targetDir.absolutePath
                )
            } catch (ex: Exception) {
                InstallResult(false, "تعذر استعادة النسخة الاحتياطية: ${ex.localizedMessage ?: ex.javaClass.simpleName}")
            }
        }

    suspend fun deployPreparedPackage(
        context: Context,
        preparedPath: String,
        gamePackage: String,
        autoBackup: Boolean,
        onStatus: (String) -> Unit
    ): InstallResult = withContext(Dispatchers.IO) {
        val src = File(preparedPath.trim())
        if (!src.exists()) {
            return@withContext InstallResult(false, "الملف أو المجلد المجهز غير موجود.")
        }

        if (autoBackup) {
            withContext(Dispatchers.Main) {
                onStatus("جاري أخذ نسخة احتياطية قبل النشر...")
            }
            backupTargetPaks(context, gamePackage)
        }

        val targetDir = getGameAndroidDataTargetDir(gamePackage)
        withContext(Dispatchers.Main) {
            onStatus("جاري تجهيز مجلد الهدف ونقل الملفات...")
        }

        try {
            targetDir.mkdirs()
            if (src.isDirectory) {
                src.copyRecursively(targetDir, overwrite = true)
            } else {
                val destFile = File(targetDir, src.name)
                src.copyTo(destFile, overwrite = true)
            }
            return@withContext InstallResult(
                true,
                "تم نقل الحزمة بنجاح إلى: ${targetDir.absolutePath}",
                targetDir.absolutePath
            )
        } catch (directEx: Exception) {
            val shzStatus = inspectShizuku(context)
            if (shzStatus == ShizukuStatus.READY) {
                val cmd = if (src.isDirectory) {
                    "mkdir -p '${targetDir.absolutePath}' && cp -rf '${src.absolutePath}/.' '${targetDir.absolutePath}/'"
                } else {
                    "mkdir -p '${targetDir.absolutePath}' && cp -f '${src.absolutePath}' '${targetDir.absolutePath}/${src.name}'"
                }
                val (ok, info) = executeShizukuCommand(cmd)
                if (ok) {
                    return@withContext InstallResult(
                        true,
                        "تم النشر عبر Shizuku بنجاح إلى: ${targetDir.absolutePath}",
                        targetDir.absolutePath
                    )
                }
                return@withContext InstallResult(false, "تعذر النشر عبر Shizuku: $info")
            }
            return@withContext InstallResult(
                false,
                "تعذر الكتابة المباشرة (${directEx.localizedMessage ?: "صلاحيات Android/data"}) وShizuku غير جاهز."
            )
        }
    }

    suspend fun downloadAndPrepare(
        context: Context,
        downloadUrl: String,
        fileName: String,
        expectedSha256: String,
        deployMode: String,
        onProgress: (Float, String) -> Unit
    ): InstallResult = withContext(Dispatchers.IO) {
        val cleanUrl = downloadUrl.trim()
        if (!cleanUrl.startsWith("https://") && !cleanUrl.startsWith("http://")) {
            return@withContext InstallResult(false, "رابط التحميل غير صالح.")
        }

        val targetName = File(fileName.trim()).name
            .replace(Regex("[^A-Za-z0-9._-]"), "_")
            .ifBlank { AppConfig.DEFAULT_TARGET_FILE }
            .take(120)

        val outDir = getTargetPackagesDir(context)
        val tempFile = File(outDir, "$targetName.part")
        val finalFile = File(outDir, targetName)

        withContext(Dispatchers.Main) {
            onProgress(0.05f, "جاري الاتصال بخادم التحميل...")
        }

        var conn: HttpURLConnection? = null
        try {
            conn = (URL(cleanUrl).openConnection() as HttpURLConnection).apply {
                connectTimeout = AppConfig.CONNECT_TIMEOUT_MS
                readTimeout = AppConfig.READ_TIMEOUT_MS
                setRequestProperty("User-Agent", "LaderTareiq/${AppConfig.APP_VERSION} (Android; Kotlin)")
            }

            val totalBytes = conn.contentLengthLong
            if (totalBytes > AppConfig.MAX_DOWNLOAD_BYTES) {
                return@withContext InstallResult(false, "حجم الملف يتجاوز الحد الأقصى المسموح.")
            }

            var downloaded = 0L
            BufferedInputStream(conn.inputStream).use { input ->
                FileOutputStream(tempFile).use { output ->
                    val buffer = ByteArray(65536)
                    var count = input.read(buffer)
                    while (count != -1) {
                        downloaded += count
                        if (downloaded > AppConfig.MAX_DOWNLOAD_BYTES) {
                            output.close()
                            tempFile.delete()
                            return@withContext InstallResult(false, "تم إيقاف التحميل لتجاوز الحد الأقصى.")
                        }
                        output.write(buffer, 0, count)
                        val prog = if (totalBytes > 0L) {
                            (0.05f + 0.80f * (downloaded.toFloat() / totalBytes.toFloat())).coerceIn(0.05f, 0.85f)
                        } else {
                            0.45f
                        }
                        val statusText = if (totalBytes > 0L) {
                            val doneMb = downloaded / (1024.0 * 1024.0)
                            val totMb = totalBytes / (1024.0 * 1024.0)
                            String.format(Locale.US, "جاري التحميل: %.1f / %.1f MB", doneMb, totMb)
                        } else {
                            val doneMb = downloaded / (1024.0 * 1024.0)
                            String.format(Locale.US, "جاري التحميل: %.1f MB", doneMb)
                        }
                        withContext(Dispatchers.Main) {
                            onProgress(prog, statusText)
                        }
                        count = input.read(buffer)
                    }
                }
            }

            if (!tempFile.exists() || tempFile.length() == 0L) {
                tempFile.delete()
                return@withContext InstallResult(false, "الملف المحمّل فارغ أو غير مكتمل.")
            }

            val actualSha = computeSha256(tempFile)
            val shaClean = expectedSha256.trim().lowercase(Locale.US)
            if (shaClean.isNotEmpty()) {
                withContext(Dispatchers.Main) {
                    onProgress(0.88f, "جاري التحقق من بصمة SHA-256...")
                }
                if (actualSha != shaClean) {
                    tempFile.delete()
                    return@withContext InstallResult(false, "فشل التحقق من SHA-256: الملف غير مطابق للبصمة.")
                }
            }

            if (finalFile.exists()) finalFile.delete()
            if (!tempFile.renameTo(finalFile)) {
                tempFile.copyTo(finalFile, overwrite = true)
                tempFile.delete()
            }

            val modeClean = deployMode.trim().lowercase(Locale.US)
            if (finalFile.extension.lowercase(Locale.US) == "zip" && (modeClean == "auto" || modeClean == "folder")) {
                withContext(Dispatchers.Main) {
                    onProgress(0.94f, "جاري فك ضغط الأرشيف بأمان...")
                }
                val extRes = extractZipLocally(context, finalFile.absolutePath)
                if (!extRes.ok) {
                    return@withContext InstallResult(false, extRes.message)
                }
                withContext(Dispatchers.Main) {
                    onProgress(1.0f, "تم تجهيز الحزمة وفك الضغط بنجاح.")
                }
                return@withContext InstallResult(
                    true,
                    "تم التجهيز وفك الضغط في: ${extRes.outputPath}",
                    extRes.outputPath,
                    actualSha
                )
            }

            withContext(Dispatchers.Main) {
                onProgress(1.0f, "تم تحميل الملف وتجهيزه بنجاح.")
            }
            InstallResult(
                true,
                "تم حفظ الملف في: ${finalFile.absolutePath}",
                finalFile.absolutePath,
                actualSha
            )
        } catch (ex: Exception) {
            tempFile.delete()
            InstallResult(false, "حدث خطأ أثناء التحميل: ${ex.localizedMessage ?: ex.javaClass.simpleName}")
        } finally {
            conn?.disconnect()
        }
    }
}
