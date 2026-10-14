# Runbook: Cihaz Hazırlığı (A0.07)

Bir telefonu mphone ile kullanılabilir hale getirmek için adım adım rehber. Her telefon hazırlandıktan sonra [inventory.md](../inventory.md)'ye eklenir.

> **İki tür cihaz var, kurallar farklı:**
> - **Raf cihazı** (şirkete ait, yalnızca otomasyon için): ekran kilidi yok, şarjda uyanık kalır.
> - **Kişisel/çalışan cihazı:** ekran kilidi **kalır**; kilit açmak her zaman insanın işidir. Ayar değiştirmeden önce sahibine sorulur.

---

## 1. Android — tüm markalar

### 1.1 Geliştirici seçenekleri
1. **Ayarlar → Telefon hakkında** (Samsung: *Telefon hakkında → Yazılım bilgileri*; Xiaomi: *Telefon hakkında → Tüm özellikler*).
2. **Yapım numarası**'na (Samsung) / **MIUI/HyperOS sürümü**'ne (Xiaomi) 7 kez dokun → "Artık bir geliştiricisiniz".
3. **Ayarlar → Sistem → Geliştirici seçenekleri** (Samsung: Ayarlar'ın en altında).

### 1.2 Geliştirici seçenekleri içinde
| Ayar | Değer | Neden |
|---|---|---|
| USB hata ayıklama | **Açık** | adb erişimi |
| Pencere/Geçiş/Animatör animasyon ölçeği | **0.5x** (raf: **Kapalı**) | uiautomator "idle state" hatalarını azaltır (PITFALLS#android-idle-state) |
| Şarj olurken uyanık kal | Raf: **Açık** · Kişisel: Kapalı | Ekran zaman aşımıyla kilitlenme |
| Kablosuz hata ayıklama | Yalnızca Wi-Fi kullanılacaksa | Yeniden başlatmada kapanır (PITFALLS#android-wireless-debug-resets) |
| İşaretçi konumu / Dokunmaları göster | Hata ayıklarken açılabilir | Dokunuşların nereye gittiğini görmek |

### 1.3 İlk bağlantı (USB)
1. Telefonu kaliteli, kısa, veri destekli kabloyla bağla (mümkünse powered hub).
2. Telefonun kilidini aç → **"USB hata ayıklamaya izin verilsin mi?"** → **"Bu bilgisayardan her zaman izin ver"** işaretle → **İzin ver**.
3. Host'ta: `adb devices -l` → cihaz `device` durumunda olmalı (`unauthorized` ise 2. adımı tekrarla; istem çıkmazsa kabloyu çıkar-tak).
4. `uv run mphone doctor android` (P2'den itibaren) → tüm adımlar yeşil.
5. Türkçe yazım için: `uv run mphone android ime install` (P2, A2.09).

### 1.4 Wi-Fi (Android 11+, host ile aynı ağ)
1. Geliştirici seçenekleri → **Kablosuz hata ayıklama** açık → satıra dokun → **Eşleme koduyla cihaz eşle**.
2. Host'ta: `uv run mphone android pair <6 haneli kod>` (P2, A2.14).
3. Telefon adıyla hatırlanır; sonrasında mDNS ile bulunur.

### 1.5 Diğer ayarlar
| Ayar | Raf | Kişisel |
|---|---|---|
| Ekran kilidi | Yok | Kalır (kilit açma insanın işi) |
| Otomatik sistem güncellemesi | Kapalı (sürüm sabit) | Sahibine bırak |
| Play Store otomatik uygulama güncellemesi | Kapalı veya yalnızca Wi-Fi + gece | Sahibine bırak |
| Pil koruma (şarjı %80'de sınırla) | **Açık** (Samsung: *Pil → Diğer pil ayarları → Pili koru*) | Sahibine bırak |
| Dil | Görevlere göre (Türkçe varsayılan) | — |
| Bildirim önizlemeleri | Görev gerektiriyorsa açık | — |

## 2. Marka özel adımlar

### 2.1 Samsung (One UI)
- Geliştirici seçenekleri Ayarlar listesinin en altında görünür.
- **Otomatik engelleyici** (Ayarlar → Güvenlik ve gizlilik) açıksa USB üzerinden APK kurulumunu engeller → IME kurulumu için kapat.
- "Uyku modundaki uygulamalar": Companion App (P7) için hariç tut.

### 2.2 Xiaomi / Redmi / POCO (MIUI / HyperOS)
- Geliştirici seçeneklerinde ayrıca: **USB üzerinden yükle** (Mi hesabı ve SIM gerekebilir) ve **USB hata ayıklama (Güvenlik ayarları)** — ikisi de **açık**; aksi halde `input` komutları ve APK kurulumu sessizce başarısız olur (PITFALLS#android-miui-restrictions).
- **MIUI optimizasyonu**nu kapatmak bazı sürümlerde uiautomator'ı düzeltir (Geliştirici seçeneklerinin en altı).
- Otomatik başlatma ve pil tasarrufu: Companion App için "Kısıtlama yok".

### 2.3 Google Pixel
- Referans cihaz; ek adım yok.

### 2.4 Huawei / Honor / Oppo / Realme
- Arka plan uygulama yönetimi agresiftir; Companion App için "Manuel yönet → hepsi açık". (P7'de genişletilecek.)

## 3. iPhone — iPhone Mirroring (P4)

Gereksinimler: macOS 15 Sequoia+ olan Mac, iOS 18+ iPhone, **aynı Apple ID**, iki cihazda Bluetooth + Wi-Fi açık, iPhone Mac'in yakınında.

1. Mac'te **iPhone Mirroring** uygulamasını aç → yönergeleri izle (iPhone'da onay gerekir).
2. **Sistem Ayarları → Gizlilik ve Güvenlik**:
   - **Erişilebilirlik** → mphone'u çalıştıran uygulama (Terminal / iTerm / node servisi) — anında etkili.
   - **Ekran Kaydı** → aynı uygulama — uygulama **yeniden başlatılınca** etkili.
3. iPhone'u **kilitle** (Mirroring yalnızca kilitliyken bağlanır; açınca "iPhone in Use" olur).
4. `uv run mphone doctor ios` (P4, A4.07).

Mac node ise (raf): otomatik oturum açma açık, ekran koruyucu/uyku/ekran kilidi kapalı, macOS otomatik güncelleme kapalı (davranış değişikliği riski, PITFALLS#ios-vertical-drag-dropped).

## 4. Kontrol listesi (her cihaz için)

- [ ] Envantere eklendi (model, OS, seri hash, sahip, konum, tür: raf/kişisel)
- [ ] Geliştirici seçenekleri + USB hata ayıklama + "her zaman izin ver"
- [ ] Animasyon ölçekleri ayarlandı
- [ ] (Raf) şarjda uyanık, kilit yok, güncellemeler kapalı, pil koruma açık
- [ ] Marka özel adımlar
- [ ] `mphone doctor` yeşil
- [ ] Türkçe yazım testi (`mphone doctor android --write-test`) geçti
- [ ] Fiziksel etiket (QR = cihaz kimliği) yapıştırıldı
