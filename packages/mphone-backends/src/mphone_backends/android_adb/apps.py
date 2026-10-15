"""Names people say → package ids (A2.11).

adb cannot read app labels without aapt on the host, so common apps are listed here in Turkish
and English; anything else matches by its package id or a fragment of it. The Companion App (P7)
reads real labels from the launcher.
"""

ALIASES: dict[str, tuple[str, ...]] = {
    "Ayarlar": ("com.android.settings",),
    "Settings": ("com.android.settings",),
    "WhatsApp": ("com.whatsapp",),
    "WhatsApp Business": ("com.whatsapp.w4b",),
    "Chrome": ("com.android.chrome",),
    "Instagram": ("com.instagram.android",),
    "Telegram": ("org.telegram.messenger",),
    "Gmail": ("com.google.android.gm",),
    "YouTube": ("com.google.android.youtube",),
    "Haritalar": ("com.google.android.apps.maps",),
    "Maps": ("com.google.android.apps.maps",),
    "Play Store": ("com.android.vending",),
    "Telefon": ("com.google.android.dialer", "com.samsung.android.dialer", "com.android.dialer"),
    "Phone": ("com.google.android.dialer", "com.samsung.android.dialer", "com.android.dialer"),
    "Mesajlar": ("com.google.android.apps.messaging", "com.samsung.android.messaging"),
    "Messages": ("com.google.android.apps.messaging", "com.samsung.android.messaging"),
    "Kişiler": ("com.google.android.contacts", "com.samsung.android.app.contacts", "com.android.contacts"),
    "Contacts": ("com.google.android.contacts", "com.samsung.android.app.contacts", "com.android.contacts"),
    "Takvim": ("com.google.android.calendar", "com.samsung.android.calendar"),
    "Calendar": ("com.google.android.calendar", "com.samsung.android.calendar"),
    "Saat": ("com.google.android.deskclock", "com.sec.android.app.clockpackage"),
    "Clock": ("com.google.android.deskclock", "com.sec.android.app.clockpackage"),
    "Hesap Makinesi": ("com.google.android.calculator", "com.sec.android.app.popupcalculator"),
    "Calculator": ("com.google.android.calculator", "com.sec.android.app.popupcalculator"),
    "Kamera": ("com.google.android.GoogleCamera", "com.sec.android.app.camera", "com.android.camera2"),
    "Camera": ("com.google.android.GoogleCamera", "com.sec.android.app.camera", "com.android.camera2"),
    "Fotoğraflar": ("com.google.android.apps.photos",),
    "Photos": ("com.google.android.apps.photos",),
    "Galeri": ("com.sec.android.gallery3d", "com.miui.gallery"),
    "Gallery": ("com.sec.android.gallery3d", "com.miui.gallery"),
    "Dosyalar": ("com.google.android.apps.nbu.files", "com.google.android.documentsui"),
    "Files": ("com.google.android.apps.nbu.files", "com.google.android.documentsui"),
    "Notlar": ("com.google.android.keep", "com.samsung.android.app.notes", "com.miui.notes"),
    "Keep": ("com.google.android.keep",),
    "Notes": ("com.samsung.android.app.notes", "com.miui.notes", "com.google.android.keep"),
    "mphone test": ("com.milyonus.mphone.ime",),
}


def label_for(package: str) -> str | None:
    """The first alias naming this package (Turkish first), for listing apps."""
    for label, ids in ALIASES.items():
        if package in ids:
            return label
    return None
