package com.ladertareiq.app

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material.icons.outlined.Backup
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.DeleteSweep
import androidx.compose.material.icons.outlined.FolderOpen
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Restore
import androidx.compose.material.icons.outlined.Security
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.SupportAgent
import androidx.compose.material.icons.outlined.Terminal
import androidx.compose.material.icons.outlined.UploadFile
import androidx.compose.material.icons.outlined.VerifiedUser
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ladertareiq.app.data.ApiClient
import com.ladertareiq.app.data.AppConfig
import com.ladertareiq.app.data.AppState
import com.ladertareiq.app.data.PackageInstallerManager
import com.ladertareiq.app.data.PreparedPackageItem
import com.ladertareiq.app.data.ShizukuStatus
import com.ladertareiq.app.data.StateStore
import com.ladertareiq.app.ui.theme.ColorAmber
import com.ladertareiq.app.ui.theme.ColorBg
import com.ladertareiq.app.ui.theme.ColorBgAlt
import com.ladertareiq.app.ui.theme.ColorCard
import com.ladertareiq.app.ui.theme.ColorCardBorder
import com.ladertareiq.app.ui.theme.ColorCardElevated
import com.ladertareiq.app.ui.theme.ColorCyan
import com.ladertareiq.app.ui.theme.ColorGreen
import com.ladertareiq.app.ui.theme.ColorMuted
import com.ladertareiq.app.ui.theme.ColorPink
import com.ladertareiq.app.ui.theme.ColorText
import com.ladertareiq.app.ui.theme.ColorViolet
import com.ladertareiq.app.ui.theme.LaderTareiqTheme
import kotlinx.coroutines.launch
import java.util.Locale

class MainActivity : ComponentActivity() {
    private lateinit var store: StateStore
    private var stateHolder = mutableStateOf(AppState())
    private var storageGrantedHolder = mutableStateOf(false)
    private var shizukuStatusHolder = mutableStateOf(ShizukuStatus.NOT_INSTALLED)
    private var preparedItemsHolder = mutableStateOf<List<PreparedPackageItem>>(emptyList())

    private val mediaPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) {
        refreshPermissions()
    }

    private val shizukuPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) {
        refreshPermissions()
    }

    fun refreshPermissions() {
        storageGrantedHolder.value = PackageInstallerManager.hasStoragePermissions(this)
        shizukuStatusHolder.value = PackageInstallerManager.inspectShizuku(this)
        preparedItemsHolder.value = PackageInstallerManager.listPreparedItems(this)
    }

    fun requestStorageAccess() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && !Environment.isExternalStorageManager()) {
            try {
                val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                    data = Uri.parse("package:$packageName")
                }
                startActivity(intent)
                return
            } catch (_: Exception) {
            }
        }
        val perms = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            arrayOf(
                android.Manifest.permission.READ_MEDIA_IMAGES,
                android.Manifest.permission.READ_MEDIA_VIDEO,
                android.Manifest.permission.READ_MEDIA_AUDIO
            )
        } else {
            arrayOf(
                android.Manifest.permission.READ_EXTERNAL_STORAGE,
                android.Manifest.permission.WRITE_EXTERNAL_STORAGE
            )
        }
        mediaPermissionLauncher.launch(perms)
    }

    fun requestShizukuAccess() {
        val current = PackageInstallerManager.inspectShizuku(this)
        when (current) {
            ShizukuStatus.NOT_INSTALLED, ShizukuStatus.INSTALLED_SERVICE_STOPPED -> {
                PackageInstallerManager.openShizukuApp(this)
            }
            ShizukuStatus.PERMISSION_REQUIRED -> {
                try {
                    shizukuPermissionLauncher.launch(AppConfig.SHIZUKU_PERMISSION)
                } catch (_: Exception) {
                    PackageInstallerManager.openShizukuApp(this)
                }
            }
            ShizukuStatus.READY -> {
                refreshPermissions()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = StateStore(this)
        stateHolder.value = store.load()
        refreshPermissions()
        requestStorageAccess()
        requestShizukuAccess()

        setContent {
            LaderTareiqTheme {
                LaderTareiqScreen(
                    store = store,
                    state = stateHolder.value,
                    onStateChange = { stateHolder.value = it },
                    storageGranted = storageGrantedHolder.value,
                    shizukuStatus = shizukuStatusHolder.value,
                    preparedItems = preparedItemsHolder.value,
                    onRefreshPrepared = { refreshPermissions() },
                    onRequestStorage = { requestStorageAccess() },
                    onRequestShizuku = { requestShizukuAccess() }
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refreshPermissions()
        if (::store.isInitialized) {
            stateHolder.value = store.load()
        }
    }
}

private fun statusMeta(status: String): Pair<Color, String> = when (status.lowercase(Locale.ROOT)) {
    "active" -> ColorGreen to "مفعّل ونشط"
    "expired" -> ColorAmber to "منتهي الصلاحية"
    "banned" -> ColorPink to "محظور"
    "device_limit" -> ColorAmber to "مرتبط بجهاز آخر"
    "maintenance" -> ColorViolet to "وضع الصيانة"
    else -> ColorMuted to "غير مفعّل"
}

private fun shizukuMeta(status: ShizukuStatus): Pair<Color, String> = when (status) {
    ShizukuStatus.READY -> ColorGreen to "Shizuku متصل ومصرّح"
    ShizukuStatus.PERMISSION_REQUIRED -> ColorAmber to "Shizuku نشط — مطلوب إذن"
    ShizukuStatus.INSTALLED_SERVICE_STOPPED -> ColorAmber to "Shizuku مثبّت — الخدمة متوقفة"
    ShizukuStatus.NOT_INSTALLED -> ColorPink to "Shizuku غير مثبّت"
}

@Composable
private fun LaderTareiqScreen(
    store: StateStore,
    state: AppState,
    onStateChange: (AppState) -> Unit,
    storageGranted: Boolean,
    shizukuStatus: ShizukuStatus,
    preparedItems: List<PreparedPackageItem>,
    onRefreshPrepared: () -> Unit,
    onRequestStorage: () -> Unit,
    onRequestShizuku: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val snackbarHostState = remember { SnackbarHostState() }
    var selectedTab by remember { mutableIntStateOf(0) }
    var licenseInput by remember(state.licenseKey) { mutableStateOf(state.licenseKey) }
    var packageInput by remember(state.gamePackage) {
        mutableStateOf(state.gamePackage.ifBlank { AppConfig.DEFAULT_GAME_PACKAGE })
    }
    var isBusy by remember { mutableStateOf(false) }
    var progressValue by remember { mutableFloatStateOf(0f) }
    var progressText by remember { mutableStateOf("") }
    var showProgress by remember { mutableStateOf(false) }

    val deviceId = remember { store.getDeviceId() }

    fun notify(msg: String) {
        scope.launch {
            snackbarHostState.showSnackbar(msg)
        }
    }

    fun copyToClipboard(label: String, text: String) {
        val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText(label, text))
        notify("تم نسخ $label إلى الحافظة.")
    }

    fun openExternalUrl(rawUrl: String) {
        val clean = rawUrl.trim()
        if (!clean.startsWith("https://") && !clean.startsWith("http://")) {
            notify("لا يوجد رابط متاح حالياً.")
            return
        }
        try {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(clean)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        } catch (_: Exception) {
            notify("تعذر فتح الرابط على الجهاز.")
        }
    }

    suspend fun performSync(silent: Boolean) {
        val cfg = ApiClient.fetchAppConfig()
        if (cfg.ok) {
            val remoteOta = cfg.fields["ota_version"]?.takeIf { it.isNotBlank() } ?: state.otaVersion
            val otaRes = ApiClient.fetchOtaBundle(remoteOta)
            val updated = store.save { cur ->
                cur.copy(
                    maintenance = cfg.fields["maintenance"]?.toBooleanStrictOrNull() ?: false,
                    notice = cfg.fields["notice"] ?: cur.notice,
                    supportUrl = cfg.fields["support_url"] ?: cur.supportUrl,
                    latestAppVersion = cfg.fields["latest_app_version"] ?: cur.latestAppVersion,
                    updateUrl = cfg.fields["update_url"] ?: cur.updateUrl,
                    updateMessage = cfg.fields["update_message"] ?: cur.updateMessage,
                    latestPatchVersion = cfg.fields["patch_version"] ?: cur.latestPatchVersion,
                    otaVersion = if (otaRes.ok) (otaRes.fields["ota_version"] ?: remoteOta) else cur.otaVersion,
                    otaNotes = if (otaRes.ok) (otaRes.fields["notes"] ?: cur.otaNotes) else cur.otaNotes
                )
            }
            val logged = store.addLog("success", "تمت مزامنة الإعدادات وOTA.")
            onStateChange(
                logged.copy(
                    maintenance = updated.maintenance,
                    notice = updated.notice,
                    latestAppVersion = updated.latestAppVersion,
                    otaVersion = updated.otaVersion,
                    otaNotes = updated.otaNotes
                )
            )
            if (!silent) notify("تمت مزامنة الإعدادات بنجاح.")
        } else {
            val logged = store.addLog("warn", cfg.message)
            onStateChange(logged)
            if (!silent) notify(cfg.message)
        }
    }

    LaunchedEffect(Unit) {
        if (state.autoSyncOnStart) {
            performSync(silent = true)
        }
    }

    fun runVerify() {
        if (isBusy) return
        scope.launch {
            isBusy = true
            try {
                val res = ApiClient.verifyLicense(licenseInput, deviceId)
                val stCode = res.fields["status"] ?: if (res.ok) "active" else "inactive"
                val activePkg = packageInput.trim().ifBlank { AppConfig.DEFAULT_GAME_PACKAGE }
                val next = if (res.ok && stCode.equals("active", ignoreCase = true)) {
                    store.save { cur ->
                        cur.copy(
                            licenseKey = licenseInput.trim().uppercase(Locale.US),
                            licenseStatus = "active",
                            licenseMessage = res.message,
                            licenseType = res.fields["type"] ?: cur.licenseType,
                            expiresAt = res.fields["expires_at"] ?: cur.expiresAt,
                            remainingDays = res.fields["remaining_days"]?.toIntOrNull() ?: cur.remainingDays,
                            remainingHours = res.fields["remaining_hours"]?.toIntOrNull() ?: cur.remainingHours,
                            totalDays = res.fields["total_days"]?.toIntOrNull() ?: cur.totalDays,
                            latestPatchVersion = res.fields["patch_version"] ?: cur.latestPatchVersion,
                            downloadUrl = res.fields["download_url"] ?: cur.downloadUrl,
                            targetFileName = res.fields["target_file_name"] ?: AppConfig.DEFAULT_TARGET_FILE,
                            gamePackage = res.fields["game_package"] ?: activePkg,
                            deployMode = res.fields["deploy_mode"] ?: AppConfig.DEFAULT_DEPLOY_MODE,
                            patchSha256 = res.fields["patch_sha256"] ?: cur.patchSha256,
                            patchNotes = res.fields["patch_notes"] ?: cur.patchNotes,
                            forcePatchUpdate = res.fields["force_update"]?.toBooleanStrictOrNull() ?: false
                        )
                    }
                } else {
                    store.save { cur ->
                        cur.copy(
                            licenseKey = licenseInput.trim().uppercase(Locale.US),
                            licenseStatus = stCode,
                            licenseMessage = res.message
                        )
                    }
                }
                val logged = store.addLog(if (res.ok) "success" else "error", res.message)
                onStateChange(logged.copy(gamePackage = next.gamePackage))
                notify(res.message)
            } finally {
                isBusy = false
            }
        }
    }

    suspend fun performDownload(): InstallResult {
        if (state.downloadUrl.isBlank()) {
            return InstallResult(false, "لا يوجد رابط حزمة متاح بعد؛ فعّل الكود أولاً.")
        }
        val res = PackageInstallerManager.downloadAndPrepare(
            context = context,
            downloadUrl = state.downloadUrl,
            fileName = state.targetFileName,
            expectedSha256 = state.patchSha256,
            deployMode = state.deployMode,
            onProgress = { p, t ->
                progressValue = p
                progressText = t
            }
        )
        onRefreshPrepared()
        if (res.ok) {
            val saved = store.save { cur ->
                cur.copy(
                    installedPatchVersion = cur.latestPatchVersion.ifBlank { "1" },
                    lastPreparedPath = res.outputPath,
                    lastVerifiedSha256 = res.sha256.ifBlank { cur.lastVerifiedSha256 }
                )
            }
            val logged = store.addLog("success", res.message)
            onStateChange(
                logged.copy(
                    installedPatchVersion = saved.installedPatchVersion,
                    lastPreparedPath = saved.lastPreparedPath,
                    lastVerifiedSha256 = saved.lastVerifiedSha256
                )
            )
        } else {
            val logged = store.addLog("error", res.message)
            onStateChange(logged)
        }
        return res
    }

    suspend fun performDeploy(customPath: String? = null): InstallResult {
        val targetPkg = packageInput.trim().ifBlank { AppConfig.DEFAULT_GAME_PACKAGE }
        val sourcePath = customPath ?: state.lastPreparedPath.ifBlank {
            preparedItems.firstOrNull()?.path ?: ""
        }
        if (sourcePath.isBlank()) {
            return InstallResult(false, "لا توجد حزمة جاهزة للنشر بعد.")
        }
        val res = PackageInstallerManager.deployPreparedPackage(
            context = context,
            preparedPath = sourcePath,
            gamePackage = targetPkg,
            autoBackup = state.autoBackupBeforeDeploy,
            onStatus = { st -> progressText = st }
        )
        if (res.ok) {
            val saved = store.save { cur ->
                cur.copy(
                    gamePackage = targetPkg,
                    lastDeployedTarget = res.outputPath
                )
            }
            val logged = store.addLog("success", res.message)
            onStateChange(
                logged.copy(
                    gamePackage = saved.gamePackage,
                    lastDeployedTarget = saved.lastDeployedTarget
                )
            )
        } else {
            val logged = store.addLog("error", res.message)
            onStateChange(logged)
        }
        return res
    }

    fun runDownload() {
        if (isBusy) return
        scope.launch {
            isBusy = true
            showProgress = true
            progressValue = 0.05f
            progressText = "جاري التحميل..."
            try {
                val res = performDownload()
                notify(if (res.ok) "تم تحميل الحزمة وتجهيزها بنجاح." else res.message)
            } finally {
                showProgress = false
                isBusy = false
            }
        }
    }

    fun runDeploy(customPath: String? = null) {
        if (isBusy) return
        scope.launch {
            isBusy = true
            showProgress = true
            progressValue = 0.65f
            progressText = "جاري نشر الحزمة..."
            try {
                val res = performDeploy(customPath)
                if (res.ok) {
                    progressValue = 1.0f
                    progressText = "اكتمل النشر بنجاح."
                }
                notify(if (res.ok) "تم نشر الحزمة بنجاح." else res.message)
            } finally {
                showProgress = false
                isBusy = false
            }
        }
    }

    fun runOneTapWorkflow() {
        if (isBusy) return
        scope.launch {
            isBusy = true
            showProgress = true
            progressValue = 0.05f
            progressText = "المرحلة 1/2: تحميل وفحص وتجهيز الحزمة..."
            try {
                val dlRes = performDownload()
                if (!dlRes.ok) {
                    notify(dlRes.message)
                    return@launch
                }
                progressValue = 0.85f
                progressText = "المرحلة 2/2: نسخ احتياطي ونشر الحزمة..."
                val depRes = performDeploy(dlRes.outputPath)
                if (depRes.ok) {
                    progressValue = 1.0f
                    progressText = "تم إتمام سير العمل بنجاح."
                    notify("تم التحميل والتجهيز والنشر بنقرة واحدة.")
                } else {
                    notify(depRes.message)
                }
            } finally {
                showProgress = false
                isBusy = false
            }
        }
    }

    fun runBackup() {
        if (isBusy) return
        val pkg = packageInput.trim().ifBlank { AppConfig.DEFAULT_GAME_PACKAGE }
        scope.launch {
            isBusy = true
            try {
                val res = PackageInstallerManager.backupTargetPaks(context, pkg)
                if (res.ok) {
                    val saved = store.save { it.copy(lastBackupPath = res.outputPath, lastBackupPackage = pkg) }
                    val logged = store.addLog("success", res.message)
                    onStateChange(logged.copy(lastBackupPath = saved.lastBackupPath, lastBackupPackage = saved.lastBackupPackage))
                } else {
                    val logged = store.addLog("warn", res.message)
                    onStateChange(logged)
                }
                notify(res.message)
            } finally {
                isBusy = false
            }
        }
    }

    fun runRestoreBackup() {
        if (isBusy) return
        if (state.lastBackupPath.isBlank()) {
            notify("لا توجد نسخة احتياطية محفوظة للاستعادة.")
            return
        }
        val pkg = packageInput.trim().ifBlank { state.lastBackupPackage.ifBlank { AppConfig.DEFAULT_GAME_PACKAGE } }
        scope.launch {
            isBusy = true
            try {
                val res = PackageInstallerManager.restoreTargetPaks(context, state.lastBackupPath, pkg)
                val logged = store.addLog(if (res.ok) "success" else "error", res.message)
                onStateChange(logged)
                notify(res.message)
            } finally {
                isBusy = false
            }
        }
    }

    Scaffold(
        containerColor = ColorBg,
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) },
        topBar = {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        Brush.horizontalGradient(
                            colors = listOf(ColorBgAlt, ColorCardElevated, ColorBgAlt)
                        )
                    )
                    .border(1.dp, ColorCardBorder)
                    .padding(horizontal = 16.dp, vertical = 14.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = AppConfig.APP_TITLE,
                            color = ColorText,
                            fontSize = 21.sp,
                            fontWeight = FontWeight.ExtraBold
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = AppConfig.DEVELOPER_TAGLINE,
                            color = ColorCyan,
                            fontSize = 11.5.sp
                        )
                    }
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(99.dp))
                            .background(ColorCard)
                            .border(1.dp, ColorCyan, RoundedCornerShape(99.dp))
                            .padding(horizontal = 12.dp, vertical = 5.dp)
                    ) {
                        Text(
                            text = "v${AppConfig.APP_VERSION}",
                            color = ColorCyan,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        },
        bottomBar = {
            NavigationBar(containerColor = ColorBgAlt) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Outlined.Security, contentDescription = null) },
                    label = { Text("الرئيسية") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = ColorCyan,
                        selectedTextColor = ColorCyan,
                        indicatorColor = ColorCardElevated,
                        unselectedIconColor = ColorMuted,
                        unselectedTextColor = ColorMuted
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    icon = { Icon(Icons.Outlined.Settings, contentDescription = null) },
                    label = { Text("الإعدادات") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = ColorCyan,
                        selectedTextColor = ColorCyan,
                        indicatorColor = ColorCardElevated,
                        unselectedIconColor = ColorMuted,
                        unselectedTextColor = ColorMuted
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    icon = { Icon(Icons.Outlined.History, contentDescription = null) },
                    label = { Text("السجل") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = ColorCyan,
                        selectedTextColor = ColorCyan,
                        indicatorColor = ColorCardElevated,
                        unselectedIconColor = ColorMuted,
                        unselectedTextColor = ColorMuted
                    )
                )
            }
        }
    ) { innerPadding ->
        when (selectedTab) {
            0 -> HomeTabContent(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
                    .verticalScroll(rememberScrollState())
                    .padding(14.dp),
                state = state,
                licenseInput = licenseInput,
                onLicenseInputChange = { licenseInput = it },
                packageInput = packageInput,
                onPackageInputChange = { pkg ->
                    packageInput = pkg
                    onStateChange(store.save { it.copy(gamePackage = pkg) })
                },
                storageGranted = storageGranted,
                shizukuStatus = shizukuStatus,
                preparedItems = preparedItems,
                isBusy = isBusy,
                showProgress = showProgress,
                progressValue = progressValue,
                progressText = progressText,
                onRequestStorage = onRequestStorage,
                onRequestShizuku = onRequestShizuku,
                onVerify = { runVerify() },
                onSync = {
                    if (!isBusy) {
                        scope.launch {
                            isBusy = true
                            try {
                                performSync(silent = false)
                            } finally {
                                isBusy = false
                            }
                        }
                    }
                },
                onDownload = { runDownload() },
                onDeploy = { path -> runDeploy(path) },
                onOneTap = { runOneTapWorkflow() },
                onBackup = { runBackup() },
                onRestoreBackup = { runRestoreBackup() },
                onVerifyItemSha = { item ->
                    if (!isBusy) {
                        scope.launch {
                            isBusy = true
                            try {
                                val vr = PackageInstallerManager.verifyLocalItemSha256(item.path, state.patchSha256)
                                if (vr.ok && vr.sha256.isNotBlank()) {
                                    val saved = store.save { it.copy(lastVerifiedSha256 = vr.sha256) }
                                    val logged = store.addLog("success", vr.message)
                                    onStateChange(logged.copy(lastVerifiedSha256 = saved.lastVerifiedSha256))
                                } else {
                                    val logged = store.addLog("warn", vr.message)
                                    onStateChange(logged)
                                }
                                notify(vr.message)
                            } finally {
                                isBusy = false
                            }
                        }
                    }
                },
                onExtractItemZip = { item ->
                    if (!isBusy) {
                        scope.launch {
                            isBusy = true
                            try {
                                val er = PackageInstallerManager.extractZipLocally(context, item.path)
                                onRefreshPrepared()
                                if (er.ok) {
                                    val saved = store.save { it.copy(lastPreparedPath = er.outputPath) }
                                    val logged = store.addLog("success", er.message)
                                    onStateChange(logged.copy(lastPreparedPath = saved.lastPreparedPath))
                                } else {
                                    val logged = store.addLog("error", er.message)
                                    onStateChange(logged)
                                }
                                notify(er.message)
                            } finally {
                                isBusy = false
                            }
                        }
                    }
                },
                onLaunchGame = {
                    val pkg = packageInput.trim().ifBlank { AppConfig.DEFAULT_GAME_PACKAGE }
                    val lr = PackageInstallerManager.launchTargetGame(context, pkg)
                    notify(lr.message)
                },
                onCleanPackages = {
                    val removed = PackageInstallerManager.clearPreparedPackages(context)
                    onRefreshPrepared()
                    notify("تم تنظيف $removed عنصر من الحزم المؤقتة.")
                },
                onOpenUrl = { u -> openExternalUrl(u) }
            )
            1 -> SettingsTabContent(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
                    .verticalScroll(rememberScrollState())
                    .padding(14.dp),
                state = state,
                deviceId = deviceId,
                storageGranted = storageGranted,
                shizukuStatus = shizukuStatus,
                onCopyDeviceId = { copyToClipboard("معرّف الجهاز", deviceId) },
                onRequestStorage = onRequestStorage,
                onRequestShizuku = onRequestShizuku,
                onToggleAutoSync = { enabled ->
                    onStateChange(store.save { it.copy(autoSyncOnStart = enabled) })
                },
                onToggleAutoBackup = { enabled ->
                    onStateChange(store.save { it.copy(autoBackupBeforeDeploy = enabled) })
                },
                onToggleNotifications = { enabled ->
                    onStateChange(store.save { it.copy(notificationsEnabled = enabled) })
                },
                onHealthCheck = {
                    scope.launch {
                        val health = ApiClient.checkHealth()
                        notify(if (health.ok) "السيرفر متصل وجاهز." else "تعذر الوصول إلى السيرفر.")
                    }
                },
                onOpenSupport = { openExternalUrl(state.supportUrl) }
            )
            else -> LogsTabContent(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
                    .padding(14.dp),
                state = state,
                onCopyAllLogs = {
                    val formatted = state.logs.reversed().joinToString("
") {
                        "[${it.time}] [${it.kind.uppercase(Locale.US)}] ${it.message}"
                    }
                    if (formatted.isBlank()) {
                        notify("لا توجد سجلات لنسخها.")
                    } else {
                        copyToClipboard("سجل العمليات", formatted)
                    }
                },
                onClearLogs = {
                    onStateChange(store.clearLogs())
                    notify("تم مسح السجل.")
                }
            )
        }
    }
}

@Composable
private fun SectionCard(
    title: String,
    subtitle: String,
    accent: Color,
    content: @Composable () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, ColorCardBorder, RoundedCornerShape(18.dp)),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = ColorCard)
    ) {
        Column(modifier = Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .width(5.dp)
                        .height(36.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(accent)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(text = title, color = ColorText, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                    Text(text = subtitle, color = ColorMuted, fontSize = 12.sp)
                }
            }
            HorizontalDivider(color = ColorCardBorder)
            content()
        }
    }
}

@Composable
private fun MetricBox(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(13.dp))
            .background(ColorBg)
            .border(1.dp, ColorCardBorder, RoundedCornerShape(13.dp))
            .padding(10.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(text = value, color = color, fontSize = 17.sp, fontWeight = FontWeight.ExtraBold)
        Spacer(modifier = Modifier.height(2.dp))
        Text(text = label, color = ColorMuted, fontSize = 11.sp)
    }
}

@Composable
private fun HomeTabContent(
    modifier: Modifier,
    state: AppState,
    licenseInput: String,
    onLicenseInputChange: (String) -> Unit,
    packageInput: String,
    onPackageInputChange: (String) -> Unit,
    storageGranted: Boolean,
    shizukuStatus: ShizukuStatus,
    preparedItems: List<PreparedPackageItem>,
    isBusy: Boolean,
    showProgress: Boolean,
    progressValue: Float,
    progressText: String,
    onRequestStorage: () -> Unit,
    onRequestShizuku: () -> Unit,
    onVerify: () -> Unit,
    onSync: () -> Unit,
    onDownload: () -> Unit,
    onDeploy: (String?) -> Unit,
    onOneTap: () -> Unit,
    onBackup: () -> Unit,
    onRestoreBackup: () -> Unit,
    onVerifyItemSha: (PreparedPackageItem) -> Unit,
    onExtractItemZip: (PreparedPackageItem) -> Unit,
    onLaunchGame: () -> Unit,
    onCleanPackages: () -> Unit,
    onOpenUrl: (String) -> Unit
) {
    val context = LocalContext.current
    val (stColor, stLabel) = statusMeta(state.licenseStatus)
    val (shzColor, shzLabel) = shizukuMeta(shizukuStatus)
    val activePkg = packageInput.trim().ifBlank { AppConfig.DEFAULT_GAME_PACKAGE }
    val pkgInstalled = PackageInstallerManager.isPackageInstalled(context, activePkg)
    val netConnected = PackageInstallerManager.isNetworkConnected(context)
    val freeSpace = PackageInstallerManager.formatBytes(PackageInstallerManager.getAvailableStorageBytes(context))

    val subRatio = if (state.totalDays > 0) {
        (state.remainingDays.toFloat() / state.totalDays.toFloat()).coerceIn(0f, 1f)
    } else if (state.remainingDays > 0) {
        1f
    } else {
        0f
    }

    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (state.maintenance) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, ColorPink, RoundedCornerShape(14.dp)),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF240B1B))
            ) {
                Text(
                    text = "السيرفر في وضع الصيانة حالياً؛ قد تتأثر بعض عمليات التحقق أو التحميل.",
                    color = ColorPink,
                    fontSize = 12.5.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(12.dp)
                )
            }
        }

        if (state.notice.isNotBlank()) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, ColorCyan, RoundedCornerShape(14.dp)),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = ColorBgAlt)
            ) {
                Text(
                    text = state.notice,
                    color = ColorText,
                    fontSize = 12.5.sp,
                    modifier = Modifier.padding(12.dp)
                )
            }
        }

        if (state.latestAppVersion.isNotBlank() && ApiClient.isNewerVersion(state.latestAppVersion, AppConfig.APP_VERSION)) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, ColorAmber, RoundedCornerShape(14.dp)),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E180A))
            ) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("يتوفر تحديث جديد للتطبيق", color = ColorAmber, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text(
                        text = state.updateMessage.ifBlank {
                            "يتوفر إصدار أحدث (${state.latestAppVersion}) من نسختك الحالية (${AppConfig.APP_VERSION})."
                        },
                        color = ColorText,
                        fontSize = 12.5.sp
                    )
                    if (state.updateUrl.isNotBlank()) {
                        OutlinedButton(onClick = { onOpenUrl(state.updateUrl) }) {
                            Text("فتح رابط التحديث", color = ColorAmber, fontSize = 12.sp)
                        }
                    }
                }
            }
        }

        SectionCard(
            title = "التشخيص السريع والصلاحيات",
            subtitle = "فحص الشبكة والمساحة الحرة وحالة Shizuku",
            accent = ColorAmber
        ) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                MetricBox(
                    "الشبكة",
                    if (netConnected) "متصل" else "غير متصل",
                    if (netConnected) ColorGreen else ColorPink,
                    Modifier.weight(1f)
                )
                MetricBox("المساحة الحرة", freeSpace, ColorCyan, Modifier.weight(1f))
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                    Icon(Icons.Outlined.FolderOpen, contentDescription = null, tint = if (storageGranted) ColorGreen else ColorAmber)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (storageGranted) "صلاحية المساحة مفعّلة" else "صلاحية المساحة مطلوبة",
                        color = if (storageGranted) ColorGreen else ColorAmber,
                        fontSize = 12.5.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
                OutlinedButton(onClick = onRequestStorage) {
                    Text("طلب المساحة", color = ColorCyan, fontSize = 12.sp)
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                    Icon(Icons.Outlined.Terminal, contentDescription = null, tint = shzColor)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = shzLabel,
                        color = shzColor,
                        fontSize = 12.5.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
                OutlinedButton(onClick = onRequestShizuku) {
                    Text("ربط Shizuku", color = ColorViolet, fontSize = 12.sp)
                }
            }
        }

        SectionCard(
            title = "حالة الترخيص والاشتراك",
            subtitle = "${AppConfig.DEVELOPER_NAME} — ${AppConfig.DEVELOPER_TAGLINE}",
            accent = ColorCyan
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .clip(CircleShape)
                        .background(stColor)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = stLabel, color = stColor, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                if (state.licenseType.isNotBlank()) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("• ${state.licenseType}", color = ColorCyan, fontSize = 12.sp)
                }
            }

            Text(text = state.licenseMessage, color = ColorMuted, fontSize = 12.5.sp)

            if (state.expiresAt.isNotBlank()) {
                Text("تاريخ الانتهاء: ${state.expiresAt}", color = ColorMuted, fontSize = 12.sp)
            }

            if (state.remainingDays > 0 || state.totalDays > 0) {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("نسبة صلاحية الاشتراك", color = ColorMuted, fontSize = 11.5.sp)
                        Text(
                            text = if (state.remainingDays <= 3) "قارب على الانتهاء (${state.remainingDays} يوم)" else "${state.remainingDays} يوم متبقٍ",
                            color = if (state.remainingDays <= 3) ColorAmber else ColorGreen,
                            fontSize = 11.5.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    LinearProgressIndicator(
                        progress = { subRatio },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(7.dp)
                            .clip(RoundedCornerShape(99.dp)),
                        color = if (state.remainingDays <= 3) ColorAmber else ColorGreen,
                        trackColor = ColorBgAlt
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                MetricBox("الأيام المتبقية", state.remainingDays.toString(), ColorGreen, Modifier.weight(1f))
                MetricBox(
                    "إصدار الباتش",
                    state.latestPatchVersion.ifBlank { state.installedPatchVersion.ifBlank { "-" } },
                    ColorCyan,
                    Modifier.weight(1f)
                )
                MetricBox("إصدار OTA", state.otaVersion, ColorViolet, Modifier.weight(1f))
            }

            OutlinedTextField(
                value = licenseInput,
                onValueChange = onLicenseInputChange,
                label = { Text("كود التفعيل (License Key)") },
                placeholder = { Text("LT-XXXX-YYYY-ZZZZ") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Button(
                    onClick = onVerify,
                    enabled = !isBusy,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = ColorCyan, contentColor = Color(0xFF031318)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("تحقق وفعّل", fontWeight = FontWeight.Bold)
                }
                OutlinedButton(
                    onClick = onSync,
                    enabled = !isBusy,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("فحص OTA / APK", color = ColorCyan)
                }
            }
        }

        SectionCard(
            title = "اختيار اللعبة ونشر الحزم",
            subtitle = "تحديد الحزمة، النسخ الاحتياطي، التجهيز والنشر السريع",
            accent = ColorViolet
        ) {
            Text("نسخ سريعة:", color = ColorText, fontSize = 12.5.sp, fontWeight = FontWeight.Bold)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                AppConfig.KNOWN_GAME_PACKAGES.take(3).forEach { (pkg, title) ->
                    val active = activePkg == pkg
                    FilterChip(
                        selected = active,
                        onClick = { onPackageInputChange(pkg) },
                        label = {
                            Text(
                                text = title.substringAfter("(").removeSuffix(")"),
                                fontSize = 11.sp
                            )
                        },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = ColorViolet,
                            selectedLabelColor = Color.White,
                            containerColor = ColorBg,
                            labelColor = ColorMuted
                        )
                    )
                }
            }

            OutlinedTextField(
                value = packageInput,
                onValueChange = onPackageInputChange,
                label = { Text("اسم حزمة اللعبة (Package Name)") },
                placeholder = { Text("com.tencent.ig") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            Text(
                text = "الحالة: ${if (pkgInstalled) "مثبّتة" else "غير مثبّتة"} • المسار: ${PackageInstallerManager.getGameAndroidDataTargetDir(activePkg).absolutePath}",
                color = if (pkgInstalled) ColorGreen else ColorAmber,
                fontSize = 11.5.sp
            )

            val infoText = if (state.downloadUrl.isNotBlank()) {
                "الملف: ${state.targetFileName} | النمط: ${state.deployMode} | المثبّت: ${state.installedPatchVersion.ifBlank { "غير مثبت" }}"
            } else {
                "النمط: ${state.deployMode} | المثبّت: ${state.installedPatchVersion.ifBlank { "غير مثبت" }} — فعّل الكود لاستلام الحزمة."
            }
            Text(text = infoText, color = ColorMuted, fontSize = 12.sp)

            if (state.lastVerifiedSha256.isNotBlank()) {
                Text(
                    text = "SHA-256: ${state.lastVerifiedSha256.take(18)}...",
                    color = ColorGreen,
                    fontSize = 11.5.sp
                )
            }

            if (showProgress) {
                LinearProgressIndicator(
                    progress = { progressValue },
                    modifier = Modifier.fillMaxWidth(),
                    color = ColorCyan,
                    trackColor = ColorBgAlt
                )
                Text(text = progressText, color = ColorText, fontSize = 12.sp)
            }

            Button(
                onClick = onOneTap,
                enabled = !isBusy,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = ColorCyan, contentColor = Color(0xFF031318)),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(Icons.Outlined.AutoAwesome, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text("تنفيذ شامل بنقرة واحدة (تحميل + نشر)", fontWeight = FontWeight.ExtraBold)
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onDownload,
                    enabled = !isBusy,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = ColorViolet, contentColor = Color.White),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("تحميل وتجهيز", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                }

                Button(
                    onClick = { onDeploy(null) },
                    enabled = !isBusy && (state.lastPreparedPath.isNotBlank() || preparedItems.isNotEmpty()),
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = ColorGreen, contentColor = Color(0xFF04170E)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Outlined.UploadFile, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("نشر الحزمة", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(
                    onClick = onBackup,
                    enabled = !isBusy,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Outlined.Backup, contentDescription = null, tint = ColorCyan, modifier = Modifier.size(17.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("نسخ احتياطي", color = ColorCyan, fontSize = 11.5.sp)
                }

                OutlinedButton(
                    onClick = onRestoreBackup,
                    enabled = !isBusy && state.lastBackupPath.isNotBlank(),
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Outlined.Restore, contentDescription = null, tint = ColorAmber, modifier = Modifier.size(17.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("استعادة الأصل", color = ColorAmber, fontSize = 11.5.sp)
                }

                OutlinedButton(
                    onClick = onLaunchGame,
                    enabled = !isBusy && pkgInstalled,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Outlined.PlayArrow, contentDescription = null, tint = ColorGreen, modifier = Modifier.size(17.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("تشغيل", color = ColorGreen, fontSize = 11.5.sp)
                }
            }

            if (preparedItems.isNotEmpty()) {
                HorizontalDivider(color = ColorCardBorder)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("الحزم الجاهزة (${preparedItems.size}):", color = ColorText, fontSize = 12.5.sp, fontWeight = FontWeight.Bold)
                    OutlinedButton(onClick = onCleanPackages) {
                        Icon(Icons.Outlined.DeleteSweep, contentDescription = null, tint = ColorPink, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("تنظيف", color = ColorPink, fontSize = 11.5.sp)
                    }
                }
                preparedItems.take(4).forEach { item ->
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(ColorBg)
                            .border(1.dp, ColorCardBorder, RoundedCornerShape(12.dp))
                            .padding(10.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = if (item.isDirectory) "[مجلد] ${item.name}" else item.name,
                                    color = ColorText,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = PackageInstallerManager.formatBytes(item.sizeBytes),
                                    color = ColorMuted,
                                    fontSize = 11.sp
                                )
                            }
                            OutlinedButton(onClick = { onDeploy(item.path) }) {
                                Text("نشر", color = ColorGreen, fontSize = 11.5.sp)
                            }
                        }

                        if (!item.isDirectory) {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedButton(onClick = { onVerifyItemSha(item) }) {
                                    Icon(Icons.Outlined.VerifiedUser, contentDescription = null, tint = ColorCyan, modifier = Modifier.size(15.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("فحص SHA-256", color = ColorCyan, fontSize = 11.sp)
                                }
                                if (item.isZipArchive) {
                                    OutlinedButton(onClick = { onExtractItemZip(item) }) {
                                        Text("فك ZIP", color = ColorViolet, fontSize = 11.sp)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        SectionCard(
            title = "ملاحظات التحديث عن بُعد (OTA)",
            subtitle = "تحديثات النصوص والإعدادات دون إعادة تثبيت",
            accent = ColorGreen
        ) {
            Text(text = state.otaNotes, color = ColorMuted, fontSize = 12.5.sp)
            if (state.lastDeployedTarget.isNotBlank()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Outlined.CheckCircle, contentDescription = null, tint = ColorGreen, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("آخر مسار نشر: ${state.lastDeployedTarget}", color = ColorGreen, fontSize = 11.5.sp)
                }
            }
        }
    }
}

@Composable
private fun SettingsTabContent(
    modifier: Modifier,
    state: AppState,
    deviceId: String,
    storageGranted: Boolean,
    shizukuStatus: ShizukuStatus,
    onCopyDeviceId: () -> Unit,
    onRequestStorage: () -> Unit,
    onRequestShizuku: () -> Unit,
    onToggleAutoSync: (Boolean) -> Unit,
    onToggleAutoBackup: (Boolean) -> Unit,
    onToggleNotifications: (Boolean) -> Unit,
    onHealthCheck: () -> Unit,
    onOpenSupport: () -> Unit
) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionCard(
            title = "تفضيلات التطبيق",
            subtitle = "إعدادات المزامنة والنسخ الاحتياطي والسجل",
            accent = ColorCyan
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("مزامنة تلقائية عند فتح التطبيق", color = ColorText, fontSize = 13.sp)
                Switch(
                    checked = state.autoSyncOnStart,
                    onCheckedChange = onToggleAutoSync,
                    colors = SwitchDefaults.colors(checkedThumbColor = ColorCyan, checkedTrackColor = ColorBgAlt)
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("نسخ احتياطي تلقائي قبل النشر", color = ColorText, fontSize = 13.sp)
                Switch(
                    checked = state.autoBackupBeforeDeploy,
                    onCheckedChange = onToggleAutoBackup,
                    colors = SwitchDefaults.colors(checkedThumbColor = ColorGreen, checkedTrackColor = ColorBgAlt)
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("تسجيل التنبيهات في السجل", color = ColorText, fontSize = 13.sp)
                Switch(
                    checked = state.notificationsEnabled,
                    onCheckedChange = onToggleNotifications,
                    colors = SwitchDefaults.colors(checkedThumbColor = ColorViolet, checkedTrackColor = ColorBgAlt)
                )
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onRequestStorage, modifier = Modifier.weight(1f)) {
                    Text("إذن المساحة", color = ColorCyan, fontSize = 12.sp)
                }
                OutlinedButton(onClick = onRequestShizuku, modifier = Modifier.weight(1f)) {
                    Text("إذن Shizuku", color = ColorViolet, fontSize = 12.sp)
                }
            }
        }

        SectionCard(
            title = "معلومات الجهاز والتطبيق",
            subtitle = "بيانات التعريف المحلية وفحص السيرفر والدعم",
            accent = ColorViolet
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("معرّف الجهاز: $deviceId", color = ColorMuted, fontSize = 12.5.sp, modifier = Modifier.weight(1f))
                IconButton(onClick = onCopyDeviceId) {
                    Icon(Icons.Outlined.ContentCopy, contentDescription = null, tint = ColorCyan)
                }
            }
            Text("نسخة التطبيق: ${AppConfig.APP_VERSION}", color = ColorMuted, fontSize = 12.5.sp)
            Text("حالة المساحة: ${if (storageGranted) "مفعّلة" else "غير مفعّلة"}", color = ColorMuted, fontSize = 12.5.sp)
            Text("حالة Shizuku: ${shizukuMeta(shizukuStatus).second}", color = ColorMuted, fontSize = 12.5.sp)

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = onHealthCheck,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = ColorBgAlt, contentColor = ColorCyan)
                ) {
                    Text("اختبار اتصال السيرفر", fontSize = 12.sp)
                }
                OutlinedButton(onClick = onOpenSupport, modifier = Modifier.weight(1f)) {
                    Icon(Icons.Outlined.SupportAgent, contentDescription = null, tint = ColorGreen, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("الدعم الفني", color = ColorGreen, fontSize = 12.sp)
                }
            }
        }
    }
}

@Composable
private fun LogsTabContent(
    modifier: Modifier,
    state: AppState,
    onCopyAllLogs: () -> Unit,
    onClearLogs: () -> Unit
) {
    var selectedFilter by remember { mutableStateOf("ALL") }
    val filters = listOf("ALL", "SUCCESS", "ERROR", "WARN")
    val filteredLogs = remember(state.logs, selectedFilter) {
        val rev = state.logs.reversed()
        if (selectedFilter == "ALL") rev else rev.filter { it.kind.equals(selectedFilter, ignoreCase = true) }
    }

    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("سجل العمليات والأحداث", color = ColorText, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                OutlinedButton(onClick = onCopyAllLogs) {
                    Icon(Icons.Outlined.ContentCopy, contentDescription = null, tint = ColorCyan, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("نسخ", color = ColorCyan, fontSize = 12.sp)
                }
                OutlinedButton(onClick = onClearLogs) {
                    Text("مسح", color = ColorPink, fontSize = 12.sp)
                }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            filters.forEach { f ->
                FilterChip(
                    selected = selectedFilter == f,
                    onClick = { selectedFilter = f },
                    label = { Text(f, fontSize = 11.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = ColorCyan,
                        selectedLabelColor = Color(0xFF031318),
                        containerColor = ColorCard,
                        labelColor = ColorMuted
                    )
                )
            }
        }

        if (filteredLogs.isEmpty()) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = ColorCard)
            ) {
                Text("لا توجد سجلات مطابقة للفلتر الحالي.", color = ColorMuted, fontSize = 12.5.sp, modifier = Modifier.padding(14.dp))
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(filteredLogs) { entry ->
                    val badgeColor = when (entry.kind) {
                        "success" -> ColorGreen
                        "error" -> ColorPink
                        "warn" -> ColorAmber
                        "ota" -> ColorViolet
                        else -> ColorCyan
                    }
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, ColorCardBorder, RoundedCornerShape(12.dp)),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = ColorCard)
                    ) {
                        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(entry.kind.uppercase(Locale.US), color = badgeColor, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                Text(entry.time, color = ColorMuted, fontSize = 11.sp)
                            }
                            Text(entry.message, color = ColorText, fontSize = 12.5.sp)
                        }
                    }
                }
            }
        }
    }
}
