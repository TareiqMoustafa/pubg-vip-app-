# PUBG VIP Manager

تطبيق Flet لأندرويد: يتحقق من كود التفعيل عبر سيرفر التراخيص، ثم يحمّل الباتش ويثبّته.

## الهيكل

```
.
├── .github/workflows/build.yml   # بناء APK تلقائياً
├── .gitignore
├── pyproject.toml
├── README.md
└── src/
    ├── main.py        # الواجهة ونقطة الدخول
    ├── config.py      # كل الإعدادات (روابط، مسارات، مهلات)
    ├── api.py         # التحقق من الكود + معرّف الجهاز
    └── installer.py   # التحميل + النقل + الأمر اليدوي
```

## الإعداد
عدّل `src/config.py`:
- `SERVER_URL`: رابط سيرفر التراخيص على Vercel.
- `PATCH_DOWNLOAD_URL`: رابط احتياطي (السيرفر يرسل `download_url` من `PATCH_URL`).
- `PATCH_MIRRORS`: روابط بديلة تُجرَّب تلقائياً.
- `PATCH_SHA256`: بصمة الملف للتحقق من سلامته (اختياري).

## البناء
ادفع الكود إلى `main` ثم نزّل الـ APK من تبويب Actions ← آخر تشغيل ← Artifacts.

## التشغيل محلياً
```
pip install "flet[all]==1.0.*" httpx
flet run src/main.py
```
