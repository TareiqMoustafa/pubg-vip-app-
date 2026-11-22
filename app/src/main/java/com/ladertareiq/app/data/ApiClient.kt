package com.ladertareiq.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URI
import java.net.URLEncoder
import java.util.Locale

object ApiClient {
    private val DIGITS_REGEX = Regex("""\d+""")

    fun isNewerVersion(remoteVer: String, localVer: String): Boolean {
        val rClean = remoteVer.trim()
        val lClean = localVer.trim()
        if (rClean.isEmpty() || rClean == lClean) return false
        val rParts = DIGITS_REGEX.findAll(rClean).map { it.value.toIntOrNull() ?: 0 }.toList()
        val lParts = DIGITS_REGEX.findAll(lClean).map { it.value.toIntOrNull() ?: 0 }.toList()
        val maxLen = maxOf(rParts.size, lParts.size)
        for (i in 0 until maxLen) {
            val rv = rParts.getOrElse(i) { 0 }
            val lv = lParts.getOrElse(i) { 0 }
            if (rv != lv) return rv > lv
        }
        return false
    }

    private fun extractFields(obj: JSONObject): Map<String, String> {
        val map = mutableMapOf<String, String>()
        val keys = obj.keys()
        while (keys.hasNext()) {
            val k = keys.next()
            val v = obj.opt(k)
            if (v != null && v != JSONObject.NULL) {
                map[k] = v.toString()
            }
        }
        return map
    }

    private suspend fun requestJson(
        method: String,
        endpoint: String,
        body: JSONObject? = null,
        serverUrl: String = AppConfig.SERVER_URL
    ): ApiResult = withContext(Dispatchers.IO) {
        val base = serverUrl.trim().trimEnd('/')
        if (!base.startsWith("https://") && !base.startsWith("http://")) {
            return@withContext ApiResult(false, 0, "عنوان السيرفر غير صالح.")
        }
        var conn: HttpURLConnection? = null
        try {
            val url = URI("$base$endpoint").toURL()
            conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = method.uppercase(Locale.US)
                connectTimeout = AppConfig.CONNECT_TIMEOUT_MS
                readTimeout = AppConfig.READ_TIMEOUT_MS
                setRequestProperty("Accept", "application/json")
                setRequestProperty("User-Agent", "LaderTareiq/${AppConfig.APP_VERSION} (Android; Kotlin)")
                if (body != null) {
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                    OutputStreamWriter(outputStream, Charsets.UTF_8).use { writer ->
                        writer.write(body.toString())
                        writer.flush()
                    }
                }
            }

            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else (conn.errorStream ?: conn.inputStream)
            val text = if (stream != null) {
                BufferedReader(InputStreamReader(stream, Charsets.UTF_8)).use { it.readText() }
            } else {
                ""
            }

            val parsed = try {
                if (text.isNotBlank()) JSONObject(text) else JSONObject()
            } catch (_: Exception) {
                JSONObject()
            }

            val msg = parsed.optString("message").ifBlank {
                parsed.optString("detail").ifBlank {
                    "استجابة من السيرفر (HTTP $code)."
                }
            }

            ApiResult(
                ok = code in 200..299,
                statusCode = code,
                message = msg,
                rawJson = text,
                fields = extractFields(parsed)
            )
        } catch (ex: Exception) {
            ApiResult(false, 0, "تعذر الاتصال بالسيرفر: ${ex.localizedMessage ?: ex.javaClass.simpleName}")
        } finally {
            conn?.disconnect()
        }
    }

    suspend fun checkHealth(): ApiResult = requestJson("GET", "/api/health")

    suspend fun fetchAppConfig(): ApiResult = requestJson("GET", "/api/app-config")

    suspend fun fetchOtaBundle(otaVersion: String): ApiResult {
        val encodedVersion = URLEncoder.encode(otaVersion.trim(), "UTF-8")
        return requestJson("GET", "/api/ota-bundle?ota_version=$encodedVersion")
    }

    suspend fun verifyLicense(licenseKey: String, deviceId: String): ApiResult {
        val cleanKey = licenseKey.trim().uppercase(Locale.US)
        if (cleanKey.isEmpty()) {
            return ApiResult(false, 400, "يرجى إدخال كود التفعيل أولاً.")
        }
        val payload = JSONObject().apply {
            put("key", cleanKey)
            put("device_id", deviceId.trim())
            put("app_version", AppConfig.APP_VERSION)
        }
        return requestJson("POST", "/api/verify", body = payload)
    }
}
