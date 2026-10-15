# Protokol v1 — Op Referansı

> **Üretilmiş dosya** (`tools/gen_protocol.py`). Elle düzenleme; `packages/mphone-protocol/schema/ops.v1.json`'ı değiştirip yeniden üret.
> Protokol sürümü: `1.0.0` · Op sayısı: 39 · Tasarım: Plan.md §7.

## Op'lar

| Op | Argümanlar (varsayılan) | Sonuç | Yan etki | Zaman aşımı | Açıklama |
|---|---|---|---|---|---|
| `screen.capture` | `format="png"`, `quality=85`, `max_side=null`, `path=null` | `Capture` | none | 60 sn | Ekran görüntüsü al. |
| `screen.bounds` | — | `Bounds` | none | 15 sn | Koordinat uzayının boyutları. |
| `screen.text` | `min_confidence=0.3` | `list[Box]` | none | 30 sn | Görünür metin; ağaç varsa ağaçtan, yoksa OCR. |
| `screen.text_pixels` | `min_confidence=0.3`, `langs=["tr", "en"]` | `list[Box]` | none | 30 sn | Görünür metin, zorla OCR ile. |
| `screen.stream.start` | `fps=10`, `max_side=720`, `codec="mjpeg"` | `StreamRef` | none | 15 sn | Canlı görüntü akışını başlat. |
| `screen.stream.stop` | `stream_id` | `None` | none | 15 sn | Canlı görüntü akışını durdur. |
| `input.tap` | `x`, `y` | `None` | input | 15 sn | Bir noktaya dokun. |
| `input.press` | `x`, `y`, `duration=0.8` | `None` | input | 15 sn | Uzun bas. |
| `input.drag` | `x1`, `y1`, `x2`, `y2`, `duration=0.35`, `steps=14` | `None` | input | 15 sn | Bir noktadan diğerine sürükle (parmak hareketi). |
| `input.scroll` | `x`, `y`, `dy`, `dx=0`, `steps=6` | `None` | input | 15 sn | İçeriği kaydır, momentumsuz. dy>0 aşağıdaki içeriği gösterir. |
| `input.keys` | `combo` | `None` | input | 15 sn | Tuş veya kombinasyon bas ("enter", "back", "cmd+space"). |
| `input.text` | `s`, `mode="auto"`, `delay=0.03` | `TextResult` | input | 60 sn | Odaklı alana metin yaz (Unicode). |
| `input.clear` | — | `None` | input | 15 sn | Odaklı alanı temizle. |
| `nav.home` | — | `None` | nav | 15 sn | Ana ekrana git. |
| `nav.back` | — | `None` | nav | 15 sn | Sistem Geri. |
| `nav.recents` | — | `None` | nav | 15 sn | Son uygulamaları aç. |
| `nav.notifications` | — | `None` | nav | 15 sn | Bildirim panelini aç. |
| `apps.launch` | `name`, `fresh=false` | `AppRef` | apps | 90 sn | Uygulamayı adıyla, paket kimliğiyle veya bir parçasıyla aç. |
| `apps.current` | — | `AppRef | None` | none | 15 sn | Ön plandaki uygulama. |
| `apps.list` | `include_system=false` | `list[AppInfo]` | none | 90 sn | Yüklü uygulamalar. |
| `apps.stop` | `app_id` | `None` | apps | 15 sn | Uygulamayı durdur. |
| `apps.install` | `artifact_id=null`, `url=null`, `path=null` | `AppRef` | apps | 300 sn | Uygulama yükle (artefakt, URL veya yerel yol). |
| `apps.uninstall` | `app_id` | `None` | apps | 120 sn | Uygulamayı kaldır. |
| `device.info` | — | `DeviceInfo` | none | 15 sn | Cihaz bilgisi. |
| `device.state` | — | `DeviceState` | none | 15 sn | Cihaz durumu; 'ready' kullanılabilir demek. |
| `device.require` | — | `Bounds` | device | 30 sn | Cihazı kullanılabilir hale getir ve sınırları döndür; olmazsa kullanıcıya ne yapması gerektiğini söyleyen hata. |
| `device.detail` | — | `str` | none | 15 sn | Cihazın neden kullanılamadığı, insan dilinde. |
| `device.wake` | — | `None` | device | 15 sn | Ekranı uyandır (kilidi açmaz). |
| `device.keep_awake` | `on` | `None` | device | 15 sn | Ayar değiştirmeden ekranı uyanık tut. |
| `clipboard.get` | — | `str` | none | 15 sn | Panoyu oku. |
| `clipboard.set` | `text` | `None` | device | 15 sn | Panoya yaz. |
| `notifications.list` | `limit=50` | `list[Notification]` | none | 30 sn | Bildirimleri listele. |
| `tree` | `compressed=true` | `list[Node]` | none | 30 sn | Erişilebilirlik ağacı. |
| `ui.find` | `selector` | `list[Box]` | none | 30 sn | Seçiciyle ağaçta öğe bul. |
| `focus.probe` | — | `Any` | none | 15 sn | Kullanıcının odağının anlık görüntüsü (opak). |
| `focus.diff` | `before`, `after` | `FocusDiff` | none | 15 sn | İki odak görüntüsü arasında kullanıcı rahatsız edildi mi. |
| `files.push` | `dest`, `artifact_id=null`, `path=null` | `None` | device | 300 sn | Cihaza dosya gönder. |
| `files.pull` | `path` | `FileRef` | none | 300 sn | Cihazdan dosya al. |
| `raw` | `cmd`, `binary=false`, `timeout=60` | `Any` | device | 60 sn | Backend'e özgü kaçış kapısı (Android: adb shell). Uzak modda varsayılan kapalı. |

## Hata kodları

| Kod | Tekrar denenebilir | Anlam |
|---|---|---|
| `UNSUPPORTED` | hayır | Cihaz bu işlemi yapamaz; tekrar denemek işe yaramaz. |
| `INVALID_ARGUMENT` | hayır | Argüman şemaya uymuyor. |
| `DEVICE_OFFLINE` | evet | Cihaz veya bağlı olduğu node erişilemiyor. |
| `DEVICE_LOCKED` | hayır | Ekran kilitli; kilidi kullanıcı açmalı. |
| `DEVICE_ASLEEP` | evet | Ekran kapalı ve uyandırılamadı. |
| `DEVICE_UNAUTHORIZED` | hayır | Cihaz bu bilgisayara hata ayıklama izni vermedi. |
| `NEEDS_USER` | hayır | Fiziksel veya insan adımı gerekiyor. |
| `LEASE_REQUIRED` | hayır | Bu işlem için cihaz kiralanmalı. |
| `LEASE_CONFLICT` | evet | Cihaz başka biri tarafından kullanılıyor. |
| `LEASE_EXPIRED` | hayır | Kiralama süresi doldu. |
| `LEASE_PAUSED` | evet | Bir insan cihazın kontrolünü devraldı. |
| `POLICY_DENIED` | hayır | Politika bu işlemi reddetti. |
| `APPROVAL_REQUIRED` | evet | İşlem için insan onayı gerekiyor. |
| `APPROVAL_DENIED` | hayır | İnsan işlemi reddetti. |
| `TREE_UNAVAILABLE` | evet | Erişilebilirlik ağacı şu an alınamıyor. |
| `NOT_FOUND` | hayır | Aranan metin, öğe veya uygulama bulunamadı. |
| `TIMEOUT` | evet | İşlem süresi aşıldı. |
| `RATE_LIMITED` | evet | İşlem hızı sınırı aşıldı. |
| `INTERNAL` | hayır | Beklenmeyen hata. |

## Tipler

### ErrorInfo

| Alan | Tip | Zorunlu |
|---|---|---|
| `code` | `ErrorCode` | ✓ |
| `message` | `str` | ✓ |
| `retryable` | `bool` | ✓ |
| `user_action` | `str | None` |  |
| `details` | `dict[str, Any]` |  |

### Point

| Alan | Tip | Zorunlu |
|---|---|---|
| `x` | `int` | ✓ |
| `y` | `int` | ✓ |

### Box

Something visible on screen. x, y is the CENTRE, tap-ready, in device-local screenshot pixels (Plan.md §6.4).

| Alan | Tip | Zorunlu |
|---|---|---|
| `text` | `str` | ✓ |
| `confidence` | `float` | ✓ |
| `source` | `Source` | ✓ |
| `x` | `int` | ✓ |
| `y` | `int` | ✓ |
| `w` | `int` | ✓ |
| `h` | `int` | ✓ |
| `node_id` | `str | None` |  |
| `resource_id` | `str | None` |  |
| `content_desc` | `str | None` |  |
| `class` | `str | None` |  |
| `clickable` | `bool | None` |  |
| `clickable_ancestor` | `Point | None` |  |
| `focused` | `bool | None` |  |
| `editable` | `bool | None` |  |
| `password` | `bool | None` |  |

### Rect

| Alan | Tip | Zorunlu |
|---|---|---|
| `left` | `int` | ✓ |
| `top` | `int` | ✓ |
| `right` | `int` | ✓ |
| `bottom` | `int` | ✓ |

### Node

One accessibility-tree node, as the OS reported it.

| Alan | Tip | Zorunlu |
|---|---|---|
| `node_id` | `str` | ✓ |
| `parent_id` | `str | None` |  |
| `text` | `str` |  |
| `content_desc` | `str | None` |  |
| `resource_id` | `str | None` |  |
| `class` | `str | None` |  |
| `package` | `str | None` |  |
| `rect` | `Rect` | ✓ |
| `visible` | `bool` |  |
| `clickable` | `bool` |  |
| `enabled` | `bool` |  |
| `focused` | `bool` |  |
| `editable` | `bool` |  |
| `password` | `bool` |  |
| `scrollable` | `bool` |  |
| `checked` | `bool | None` |  |
| `selected` | `bool` |  |

### Selector

Find tree nodes. All given keys must match. Text keys compare Turkish-aware (tr_fold).

| Alan | Tip | Zorunlu |
|---|---|---|
| `query` | `str | None` |  |
| `text` | `str | None` |  |
| `text_contains` | `str | None` |  |
| `text_regex` | `str | None` |  |
| `resource_id` | `str | None` |  |
| `content_desc` | `str | None` |  |
| `class` | `str | None` |  |
| `clickable` | `bool | None` |  |
| `enabled` | `bool | None` |  |
| `within` | `Selector | None` |  |
| `index` | `int | None` |  |

### Bounds

The coordinate space of every op: device-local, 1:1 with screen.capture pixels.

| Alan | Tip | Zorunlu |
|---|---|---|
| `w` | `int` | ✓ |
| `h` | `int` | ✓ |
| `scale` | `float` |  |
| `rotation` | `Literal[0, 90, 180, 270]` |  |

### Capture

| Alan | Tip | Zorunlu |
|---|---|---|
| `w` | `int` | ✓ |
| `h` | `int` | ✓ |
| `format` | `Literal["png", "jpeg"]` | ✓ |
| `path` | `str | None` |  |
| `data_b64` | `str | None` |  |
| `artifact_id` | `str | None` |  |
| `secure` | `bool` |  |

### DeviceInfo

| Alan | Tip | Zorunlu |
|---|---|---|
| `platform` | `Literal["android", "ios", "fake"]` | ✓ |
| `os_version` | `str` | ✓ |
| `model` | `str` | ✓ |
| `manufacturer` | `str | None` |  |
| `serial_hash` | `str | None` |  |
| `battery` | `int | None` |  |
| `charging` | `bool | None` |  |
| `locale` | `str | None` |  |
| `timezone` | `str | None` |  |

### AppRef

| Alan | Tip | Zorunlu |
|---|---|---|
| `app_id` | `str` | ✓ |

### AppInfo

| Alan | Tip | Zorunlu |
|---|---|---|
| `app_id` | `str` | ✓ |
| `label` | `str | None` |  |
| `system` | `bool` |  |

### Notification

| Alan | Tip | Zorunlu |
|---|---|---|
| `app_id` | `str` | ✓ |
| `title` | `str | None` |  |
| `text` | `str | None` |  |
| `posted_at` | `str | None` |  |

### FocusDiff

| Alan | Tip | Zorunlu |
|---|---|---|
| `raised` | `bool` | ✓ |
| `stole_focus` | `bool` | ✓ |

### TextResult

| Alan | Tip | Zorunlu |
|---|---|---|
| `mode_used` | `Literal["paste", "keystrokes", "ime", "set_text"]` | ✓ |

### StreamRef

| Alan | Tip | Zorunlu |
|---|---|---|
| `stream_id` | `str` | ✓ |

### FileRef

| Alan | Tip | Zorunlu |
|---|---|---|
| `artifact_id` | `str | None` |  |
| `local_path` | `str | None` |  |

### ArtifactRef

| Alan | Tip | Zorunlu |
|---|---|---|
| `kind` | `Literal["screenshot", "tree", "video", "file", "log"]` | ✓ |
| `id` | `str` | ✓ |
| `url` | `str | None` |  |

### TraceContext

| Alan | Tip | Zorunlu |
|---|---|---|
| `trace_id` | `str` | ✓ |
| `span_id` | `str | None` |  |

### OpRequest

| Alan | Tip | Zorunlu |
|---|---|---|
| `v` | `Literal[1]` |  |
| `id` | `str` | ✓ |
| `op` | `str` | ✓ |
| `kw` | `dict[str, Any]` |  |
| `device_id` | `str | None` |  |
| `lease_id` | `str | None` |  |
| `run_id` | `str | None` |  |
| `approval_id` | `str | None` |  |
| `deadline_ms` | `int | None` |  |
| `trace` | `TraceContext | None` |  |
| `meta` | `dict[str, Any] | None` |  |

### OpResult

| Alan | Tip | Zorunlu |
|---|---|---|
| `v` | `Literal[1]` |  |
| `id` | `str` | ✓ |
| `ok` | `bool` | ✓ |
| `result` | `Any` |  |
| `error` | `ErrorInfo | None` |  |
| `duration_ms` | `int` |  |
| `artifacts` | `list[ArtifactRef]` |  |

### NodeDevice

A phone as a node reports it. local_id is the node's own name for it (android:SERIAL).

| Alan | Tip | Zorunlu |
|---|---|---|
| `local_id` | `str` | ✓ |
| `platform` | `Literal["android", "ios", "fake"]` | ✓ |
| `model` | `str | None` |  |
| `os_version` | `str | None` |  |
| `state` | `DeviceState` | ✓ |
| `transport` | `str | None` |  |
| `ops` | `list[str]` |  |

### NodeHello

node → gateway, first message after connecting.

| Alan | Tip | Zorunlu |
|---|---|---|
| `t` | `Literal["hello"]` | ✓ |
| `version` | `str` | ✓ |
| `protocol` | `str` | ✓ |
| `devices` | `list[NodeDevice]` |  |

### NodeDeviceUpdate

node → gateway: a phone appeared or changed state.

| Alan | Tip | Zorunlu |
|---|---|---|
| `t` | `Literal["device.update"]` | ✓ |
| `device` | `NodeDevice` | ✓ |

### NodeDeviceGone

node → gateway: a phone disappeared.

| Alan | Tip | Zorunlu |
|---|---|---|
| `t` | `Literal["device.gone"]` | ✓ |
| `local_id` | `str` | ✓ |

### NodeWelcome

gateway → node: ids the gateway gave the node's phones.

| Alan | Tip | Zorunlu |
|---|---|---|
| `t` | `Literal["welcome"]` | ✓ |
| `node_id` | `str` | ✓ |
| `device_map` | `dict[str, Any]` |  |

### NodeOpRequest

gateway → node: run one op on one phone.

| Alan | Tip | Zorunlu |
|---|---|---|
| `t` | `Literal["op.request"]` | ✓ |
| `req` | `str` | ✓ |
| `local_id` | `str` | ✓ |
| `op` | `str` | ✓ |
| `kw` | `dict[str, Any]` |  |
| `deadline_ms` | `int` |  |

### NodeOpResponse

node → gateway: the op's outcome. Large images travel as data_b64 in the result (artifact store: A5.12).

| Alan | Tip | Zorunlu |
|---|---|---|
| `t` | `Literal["op.response"]` | ✓ |
| `req` | `str` | ✓ |
| `ok` | `bool` | ✓ |
| `result` | `Any` |  |
| `error` | `ErrorInfo | None` |  |
| `duration_ms` | `int` |  |
