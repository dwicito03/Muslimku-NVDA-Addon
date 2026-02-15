import globalPluginHandler
import scriptHandler
import ui
import requests
import datetime
import threading
import time
import math
import config
import addonHandler
import gui
import wx
import wx.adv
import logHandler
try:
    import tones
except Exception:
    tones = None
from gui.settingsDialogs import SettingsPanel, NVDASettingsDialog
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

addonHandler.initTranslation()
log = logHandler.log

# Config
config.conf.spec["muslimku"] = {
    "language": "string(default='en')",
    "country": "string(default='Indonesia')",
    "city": "string(default='Jakarta')",
    "province": "string(default='DKI Jakarta')",
    "regency": "string(default='Jakarta Selatan')"
}

# Reminder config
config.conf.spec["muslimku"].update({
    "reminder_enabled": "boolean(default=True)",
    "reminder_offset_minutes": "integer(default=0)",
    "calculation_method": "integer(default=11)",
    "madhab": "string(default='shafi')"
})

CALC_METHODS = {
    # key: Aladhan method id
    "Jafari / Ithna Ashari": 0,
    "Karachi": 1,
    "ISNA": 2,
    "MWL": 3,
    "Umm Al-Qura": 4,
    "Egyptian": 5,
    "Tehran": 7,
    "Gulf": 8,
    "Kuwait": 9,
    "Qatar": 10,
    "Singapore": 11,
    "Turkey": 13,
    "Kemenag RI": 20,
    "Muhammadiyah": 99,
}
MUHAMMADIYAH_METHOD_SETTINGS = "18,0,18"
MADHAB_MAP = {
    "Shafi": "shafi",
    "Hanafi": "hanafi",
}
FIXED_PRAYER_OFFSETS = {
    "Fajr": 0,
    "Dhuhr": 0,
    "Asr": 0,
    "Maghrib": 0,
    "Isha": 0,
}

# Category label for Input Gestures (localized if needed)
UI_GESTURE_CATEGORY = "Muslimku"
try:
    if config.conf["muslimku"].get("language", "en") == "id":
        UI_GESTURE_CATEGORY = "Muslimku"
    else:
        UI_GESTURE_CATEGORY = "Muslimku"
except Exception:
    UI_GESTURE_CATEGORY = "Muslimku"

# Localized descriptions for Input Gestures
_ui_lang = config.conf.get("muslimku", {}).get("language", "en")
if _ui_lang == "id":
    GESTURE_DESC = {
        "fajr": "Umumkan waktu Subuh",
        "dhuhr": "Umumkan waktu Dzuhur",
        "asr": "Umumkan waktu Ashar",
        "maghrib": "Umumkan waktu Maghrib",
        "isha": "Umumkan waktu Isya",
        "imsak": "Umumkan waktu Imsak",
        "sunrise": "Umumkan waktu Terbit Fajar",
        "dhuha": "Umumkan waktu Dhuha",
        "sunset": "Umumkan waktu Matahari terbenam",
        "hari": "Umumkan hari dan tanggal",
        "next_prayer": "Umumkan waktu solat berikutnya",
        "location": "Umumkan lokasi saat ini",
        "qibla": "Periksa arah kiblat"
    }
else:
    GESTURE_DESC = {
        "fajr": "Announce Fajr time",
        "dhuhr": "Announce Dhuhr time",
        "asr": "Announce Asr time",
        "maghrib": "Announce Maghrib time",
        "isha": "Announce Isha time",
        "imsak": "Announce Imsak time",
        "sunrise": "Announce Sunrise time",
        "dhuha": "Announce Dhuha time",
        "sunset": "Announce Sunset time",
        "hari": "Announce Hijri and Gregorian date",
        "next_prayer": "Announce next prayer time",
        "location": "Announce current location",
        "qibla": "Check Qibla direction"
    }

# Daftar negara (cukup umum dan stabil)
COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Argentina",
    "Australia", "Austria", "Bangladesh", "Belgium",
    "Brazil", "Brunei", "Canada", "China",
    "Egypt", "France", "Germany", "India",
    "Indonesia", "Italy", "Japan", "Malaysia",
    "Netherlands", "Pakistan", "Saudi Arabia",
    "Singapore", "South Africa", "Thailand",
    "Turkey", "United Kingdom", "United States"
]
INDONESIA_COUNTRY = "Indonesia"
INDONESIA_PROVINCES_URL = "https://www.emsifa.com/api-wilayah-indonesia/api/provinces.json"
INDONESIA_REGENCIES_URL = "https://www.emsifa.com/api-wilayah-indonesia/api/regencies/{}.json"
GLOBAL_CITIES_BY_COUNTRY_URL = "https://countriesnow.space/api/v0.1/countries/cities"

class MuslimkuSettingsPanel(SettingsPanel):
    title = "Muslimku"
    _idnProvincesCache = None
    _idnRegenciesCache = {}
    _globalCitiesCache = {}

    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

        self.languageMap = {
            "Indonesia": "id",
            "English": "en"
        }
        self._provinceMap = {}
        self._regencyMap = {}
        self._panelClosed = False
        self._provinceLoadToken = 0
        self._regencyLoadToken = 0
        self._globalCitiesLoadToken = 0
        self.Bind(wx.EVT_WINDOW_DESTROY, self._onWindowDestroy)

        ui_lang = config.conf["muslimku"].get("language", "en")
        self._labels = {
            "panel_title": {"id": "Pengaturan Muslimku", "en": "Muslimku Settings"},
            "language": {"id": "Bahasa:", "en": "Language:"},
            "country": {"id": "Negara:", "en": "Country:"},
            "province": {"id": "Provinsi:", "en": "Province:"},
            "regency": {"id": "Kota/Kabupaten:", "en": "City/Regency:"},
            "city": {"id": "Kota:", "en": "City:"},
            "calc_method": {"id": "Metode perhitungan:", "en": "Calculation method:"},
            "madhab": {"id": "Madhab Ashar:", "en": "Asr madhab:"},
            "enable_reminders": {"id": "Aktifkan pengingat:", "en": "Enable reminders:"},
            "offset": {"id": "Ingatkan saya (menit) sebelum waktu solat:", "en": "Reminder offset (minutes):"},
            "province_load_failed": {
                "id": "Gagal memuat daftar provinsi/kabupaten. Gunakan kolom Kota.",
                "en": "Failed to load province/regency list. Please use the City field."
            },
            "city_load_failed": {
                "id": "Gagal memuat daftar kota untuk negara ini. Coba lagi beberapa saat.",
                "en": "Failed to load city list for this country. Please try again shortly."
            },
        }

        try:
            self.title = self._labels["panel_title"].get(ui_lang, "Muslimku")
        except Exception:
            self.title = "Muslimku"

        self.languageChoice = sHelper.addLabeledControl(
            self._labels["language"].get(ui_lang, "Language:"),
            wx.Choice,
            choices=list(self.languageMap.keys())
        )
        currentLang = config.conf["muslimku"]["language"]
        for label, code in self.languageMap.items():
            if code == currentLang:
                self.languageChoice.SetStringSelection(label)
                break

        self.countryChoice = sHelper.addLabeledControl(
            self._labels["country"].get(ui_lang, "Country:"),
            wx.Choice,
            choices=COUNTRIES
        )
        currentCountry = config.conf["muslimku"]["country"]
        if currentCountry in COUNTRIES:
            self.countryChoice.SetStringSelection(currentCountry)
        else:
            self.countryChoice.SetStringSelection(INDONESIA_COUNTRY)
        self.countryChoice.Bind(wx.EVT_CHOICE, self._onCountryChanged)

        self.provinceChoice = sHelper.addLabeledControl(
            self._labels["province"].get(ui_lang, "Province:"),
            wx.Choice,
            choices=[]
        )
        self.provinceChoice.Bind(wx.EVT_CHOICE, self._onProvinceChanged)

        self.regencyChoice = sHelper.addLabeledControl(
            self._labels["regency"].get(ui_lang, "City/Regency:"),
            wx.Choice,
            choices=[]
        )

        self.cityChoice = sHelper.addLabeledControl(
            self._labels["city"].get(ui_lang, "City:"),
            wx.Choice,
            choices=[]
        )

        self.cityEdit = sHelper.addLabeledControl(
            self._labels["city"].get(ui_lang, "City:"),
            wx.TextCtrl
        )
        self.cityEdit.SetValue(config.conf["muslimku"].get("city", "Jakarta"))

        self.calcMethodChoice = sHelper.addLabeledControl(
            self._labels["calc_method"].get(ui_lang, "Calculation method:"),
            wx.Choice,
            choices=list(CALC_METHODS.keys())
        )
        current_method = int(config.conf["muslimku"].get("calculation_method", 11))
        selected_method_label = None
        for lbl, val in CALC_METHODS.items():
            if int(val) == current_method:
                selected_method_label = lbl
                break
        if selected_method_label:
            self.calcMethodChoice.SetStringSelection(selected_method_label)
        else:
            self.calcMethodChoice.SetStringSelection("Singapore")

        self.madhabChoice = sHelper.addLabeledControl(
            self._labels["madhab"].get(ui_lang, "Asr madhab:"),
            wx.Choice,
            choices=list(MADHAB_MAP.keys())
        )
        saved_madhab = str(config.conf["muslimku"].get("madhab", "shafi")).lower()
        selected_madhab_label = "Shafi" if saved_madhab != "hanafi" else "Hanafi"
        self.madhabChoice.SetStringSelection(selected_madhab_label)

        enable_label = self._labels["enable_reminders"].get(ui_lang, "Enable reminders:")
        self.reminderCheck = sHelper.addLabeledControl(enable_label, wx.CheckBox)
        try:
            self.reminderCheck.SetLabel(enable_label)
            self.reminderCheck.SetName(enable_label)
            try:
                self.reminderCheck.SetToolTip(enable_label)
            except Exception:
                pass
        except Exception:
            pass
        try:
            self.reminderCheck.SetValue(bool(config.conf["muslimku"]["reminder_enabled"]))
        except Exception:
            self.reminderCheck.SetValue(True)

        self.offsetSpin = sHelper.addLabeledControl(
            self._labels["offset"].get(ui_lang, "Reminder offset (minutes):"),
            wx.SpinCtrl
        )
        self.offsetSpin.SetRange(0, 120)
        try:
            self.offsetSpin.SetValue(int(config.conf["muslimku"]["reminder_offset_minutes"]))
        except Exception:
            self.offsetSpin.SetValue(0)

        self._syncLocationControls(initial=True)

    def onSave(self):
        try:
            selectedLabel = self.languageChoice.GetStringSelection()
            config.conf["muslimku"]["language"] = self.languageMap.get(selectedLabel, "en")
            selectedCountry = self.countryChoice.GetStringSelection()
            config.conf["muslimku"]["country"] = selectedCountry

            provinceSelection = self.provinceChoice.GetStringSelection()
            regencySelection = self.regencyChoice.GetStringSelection()
            if selectedCountry == INDONESIA_COUNTRY and provinceSelection and regencySelection:
                province = provinceSelection or config.conf["muslimku"].get("province", "DKI Jakarta")
                regency = regencySelection or config.conf["muslimku"].get("regency", "Jakarta Selatan")
                city = self._normalizeIndonesiaCityName(regency)
                config.conf["muslimku"]["province"] = province
                config.conf["muslimku"]["regency"] = regency
                config.conf["muslimku"]["city"] = city
            else:
                city = self.cityChoice.GetStringSelection().strip()
                city = city or config.conf["muslimku"].get("city", "Jakarta")
                config.conf["muslimku"]["city"] = city
                config.conf["muslimku"]["province"] = ""
                config.conf["muslimku"]["regency"] = ""
            try:
                config.conf["muslimku"]["reminder_enabled"] = bool(self.reminderCheck.GetValue())
            except Exception:
                config.conf["muslimku"]["reminder_enabled"] = True
            try:
                config.conf["muslimku"]["reminder_offset_minutes"] = int(self.offsetSpin.GetValue())
            except Exception:
                config.conf["muslimku"]["reminder_offset_minutes"] = 0
            try:
                method_label = self.calcMethodChoice.GetStringSelection()
                config.conf["muslimku"]["calculation_method"] = int(CALC_METHODS.get(method_label, 11))
            except Exception:
                config.conf["muslimku"]["calculation_method"] = 11
            try:
                madhab_label = self.madhabChoice.GetStringSelection()
                config.conf["muslimku"]["madhab"] = MADHAB_MAP.get(madhab_label, "shafi")
            except Exception:
                config.conf["muslimku"]["madhab"] = "shafi"
        except Exception as e:
            try:
                ui.message("Failed to save Muslimku settings.")
            except Exception:
                pass
            return False
        # indicate success so the settings dialog may close
        return True

    def _onCountryChanged(self, evt):
        self._syncLocationControls(initial=False)
        evt.Skip()

    def _onProvinceChanged(self, evt):
        self._startRegenciesLoad(initial=False)
        evt.Skip()

    def _syncLocationControls(self, initial=False):
        is_indonesia = (self.countryChoice.GetStringSelection() == INDONESIA_COUNTRY)
        self.provinceChoice.Show(is_indonesia)
        self.regencyChoice.Show(is_indonesia)
        self.provinceChoice.Enable(False)
        self.regencyChoice.Enable(False)
        self.cityChoice.Show(not is_indonesia)
        self.cityChoice.Enable(False)
        self.cityEdit.Show(False)
        self.cityEdit.Enable(False)
        if is_indonesia:
            self._startProvincesLoad(initial=initial)
        else:
            self._startGlobalCitiesLoad(initial=initial)
        self.Layout()
        if self.Parent:
            self.Parent.Layout()

    def _onWindowDestroy(self, evt):
        self._panelClosed = True
        evt.Skip()

    def _setChoiceLoading(self, choiceCtrl, loadingText):
        try:
            choiceCtrl.SetItems([loadingText])
            choiceCtrl.SetSelection(0)
            choiceCtrl.Enable(False)
        except Exception:
            pass

    def _startProvincesLoad(self, initial=False):
        self._provinceLoadToken += 1
        token = self._provinceLoadToken
        self._setChoiceLoading(self.provinceChoice, "Loading provinces...")
        self._setChoiceLoading(self.regencyChoice, "Loading city/regency...")

        def worker():
            try:
                provinces = MuslimkuSettingsPanel._idnProvincesCache
                if not provinces:
                    response = requests.get(INDONESIA_PROVINCES_URL, timeout=6)
                    provinces = response.json()
                    if not isinstance(provinces, list) or not provinces:
                        provinces = []
                    MuslimkuSettingsPanel._idnProvincesCache = provinces
                wx.CallAfter(self._applyProvincesLoad, token, initial, provinces)
            except Exception:
                wx.CallAfter(self._applyProvincesLoad, token, initial, None)

        threading.Thread(target=worker, daemon=True).start()

    def _applyProvincesLoad(self, token, initial, provinces):
        if self._panelClosed or token != self._provinceLoadToken:
            return
        if not provinces:
            try:
                self.provinceChoice.Show(False)
                self.regencyChoice.Show(False)
                self.cityChoice.Show(False)
                self.cityEdit.Show(True)
                self.cityEdit.Enable(True)
                self.Layout()
                if self.Parent:
                    self.Parent.Layout()
                ui_lang = config.conf["muslimku"].get("language", "en")
                ui.message(self._labels["province_load_failed"].get(ui_lang, "Failed to load province/regency list. Please use the City field."))
            except Exception:
                pass
            return

        self._provinceMap = {p.get("name", ""): p.get("id", "") for p in provinces if p.get("name") and p.get("id")}
        province_names = list(self._provinceMap.keys())
        self.provinceChoice.SetItems(province_names)
        saved_province = config.conf["muslimku"].get("province", "")
        if initial and saved_province in self._provinceMap:
            self.provinceChoice.SetStringSelection(saved_province)
        elif province_names:
            self.provinceChoice.SetSelection(0)
        self.provinceChoice.Enable(bool(province_names))
        self._startRegenciesLoad(initial=initial)

    def _startRegenciesLoad(self, initial=False):
        province_name = self.provinceChoice.GetStringSelection()
        province_id = self._provinceMap.get(province_name)
        if not province_id:
            self.regencyChoice.SetItems([])
            return
        self._regencyLoadToken += 1
        token = self._regencyLoadToken
        self._setChoiceLoading(self.regencyChoice, "Loading city/regency...")

        def worker():
            try:
                regencies = MuslimkuSettingsPanel._idnRegenciesCache.get(province_id)
                if not regencies:
                    response = requests.get(INDONESIA_REGENCIES_URL.format(province_id), timeout=6)
                    regencies = response.json()
                    if not isinstance(regencies, list):
                        regencies = []
                    MuslimkuSettingsPanel._idnRegenciesCache[province_id] = regencies
                wx.CallAfter(self._applyRegenciesLoad, token, initial, regencies)
            except Exception:
                wx.CallAfter(self._applyRegenciesLoad, token, initial, None)

        threading.Thread(target=worker, daemon=True).start()

    def _applyRegenciesLoad(self, token, initial, regencies):
        if self._panelClosed or token != self._regencyLoadToken:
            return
        if regencies is None:
            try:
                log.exception("Muslimku: failed loading Indonesia regency list.")
            except Exception:
                pass
            self.regencyChoice.SetItems([])
            self.regencyChoice.Enable(False)
            return
        self._regencyMap = {r.get("name", ""): r.get("id", "") for r in regencies if r.get("name") and r.get("id")}
        regency_names = list(self._regencyMap.keys())
        self.regencyChoice.SetItems(regency_names)
        saved_regency = config.conf["muslimku"].get("regency", "")
        saved_city = config.conf["muslimku"].get("city", "")
        if initial and saved_regency in self._regencyMap:
            self.regencyChoice.SetStringSelection(saved_regency)
        elif initial and saved_city:
            for name in regency_names:
                norm = self._normalizeIndonesiaCityName(name).lower()
                if saved_city.lower() in norm or norm in saved_city.lower():
                    self.regencyChoice.SetStringSelection(name)
                    break
        elif regency_names:
            self.regencyChoice.SetSelection(0)
        self.regencyChoice.Enable(bool(regency_names))

    def _startGlobalCitiesLoad(self, initial=False):
        if self._panelClosed:
            return
        country = self.countryChoice.GetStringSelection()
        if country == INDONESIA_COUNTRY:
            return
        self._globalCitiesLoadToken += 1
        token = self._globalCitiesLoadToken
        cached = MuslimkuSettingsPanel._globalCitiesCache.get(country)
        if cached is not None:
            self._applyGlobalCitiesLoad(token, cached, initial)
            return

        self._setChoiceLoading(self.cityChoice, "Loading cities...")

        def worker():
            try:
                response = requests.post(
                    GLOBAL_CITIES_BY_COUNTRY_URL,
                    json={"country": country},
                    timeout=8
                )
                response.raise_for_status()
                payload = response.json()
                names = payload.get("data", []) if isinstance(payload, dict) else []
                if not isinstance(names, list):
                    names = []
                names = sorted({str(x).strip() for x in names if str(x).strip()})
                MuslimkuSettingsPanel._globalCitiesCache[country] = names
                wx.CallAfter(self._applyGlobalCitiesLoad, token, names, initial)
            except Exception:
                wx.CallAfter(self._applyGlobalCitiesLoad, token, None, initial)

        threading.Thread(target=worker, daemon=True).start()

    def _applyGlobalCitiesLoad(self, token, names, initial):
        if self._panelClosed or token != self._globalCitiesLoadToken:
            return
        if self.countryChoice.GetStringSelection() == INDONESIA_COUNTRY:
            return
        if names is None:
            self.cityChoice.Show(True)
            self.cityChoice.SetItems([])
            self.cityChoice.Enable(False)
            ui_lang = config.conf["muslimku"].get("language", "en")
            ui.message(self._labels["city_load_failed"].get(ui_lang, "Failed to load city list for this country. Please try again shortly."))
            self.Layout()
            if self.Parent:
                self.Parent.Layout()
            return
        self.cityChoice.Show(True)
        self.cityEdit.Show(False)
        self.cityEdit.Enable(False)
        self.cityChoice.SetItems(names)
        saved_city = config.conf["muslimku"].get("city", "")
        if initial and saved_city in names:
            self.cityChoice.SetStringSelection(saved_city)
        elif names:
            self.cityChoice.SetSelection(0)
        self.cityChoice.Enable(bool(names))
        self.Layout()
        if self.Parent:
            self.Parent.Layout()

    def _normalizeIndonesiaCityName(self, regency_name):
        if not regency_name:
            return ""
        name = regency_name.strip()
        prefixes = ("KABUPATEN ", "KOTA ")
        upper = name.upper()
        for p in prefixes:
            if upper.startswith(p):
                return name[len(p):].strip().title()
        return name.title()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self):
        super().__init__()
        if MuslimkuSettingsPanel not in NVDASettingsDialog.categoryClasses:
            NVDASettingsDialog.categoryClasses.append(MuslimkuSettingsPanel)
        # Reminder thread control
        self._stop_event = threading.Event()
        self._reminder_thread = threading.Thread(target=self._reminder_loop, daemon=True)
        self._reminder_thread.start()
        # Double-press clipboard helper
        self._last_invoke = {}
        self._double_threshold = 1.5
        # Reminder runtime cache/state.
        self._timings_cache = {"ts": 0.0, "payload": None}
        self._hijri_cache = {}
        self._notified_keys = set()
        self._notified_day = None
        self._qibla_lock = threading.Lock()
        self._qibla_busy = False

    def terminate(self):
        try:
            NVDASettingsDialog.categoryClasses.remove(MuslimkuSettingsPanel)
        except ValueError:
            pass
        # Stop reminder thread
        try:
            self._stop_event.set()
            if getattr(self, "_reminder_thread", None):
                self._reminder_thread.join(timeout=2)
        except Exception:
            pass
        super().terminate()

    def _reminder_loop(self):
        while not self._stop_event.is_set():
            try:
                enabled = bool(config.conf["muslimku"].get("reminder_enabled", True))
                if enabled:
                    self._check_reminders_once()
                # Poll every 15s to avoid missing exact trigger moments.
                for _ in range(15):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
            except Exception:
                try:
                    log.exception("Muslimku: unexpected error in reminder loop.")
                except Exception:
                    pass
                # wait a bit before retrying
                for _ in range(6):
                    if self._stop_event.is_set():
                        break
                    time.sleep(5)

    def _get_cached_timings_payload(self, cache_seconds=300):
        try:
            now_ts = time.time()
            cache = getattr(self, "_timings_cache", {})
            if cache.get("payload") and (now_ts - float(cache.get("ts", 0.0)) < cache_seconds):
                return cache.get("payload")

            response = self._fetch_timings(timeout=10)
            payload = response.json().get("data", {}) or {}
            self._timings_cache = {"ts": now_ts, "payload": payload}
            return payload
        except Exception:
            try:
                log.exception("Muslimku: failed to fetch prayer timings payload.")
            except Exception:
                pass
            return None

    def _check_reminders_once(self):
        payload = self._get_cached_timings_payload(cache_seconds=300)
        if not payload:
            return

        data = payload.get("timings", {})
        now = self._get_location_now(payload)
        if not data:
            return

        try:
            offset = int(config.conf["muslimku"].get("reminder_offset_minutes", 0))
        except Exception:
            offset = 0
        grace_seconds = 120
        day_key = now.strftime("%Y-%m-%d")

        # Reset de-duplication set when date changes at location timezone.
        if self._notified_day != day_key:
            self._notified_day = day_key
            self._notified_keys = set()

        prayers = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
        for p in prayers:
            target = self._get_adjusted_prayer_datetime(data, p, now)
            if not target:
                continue
            trigger = target - datetime.timedelta(minutes=offset)
            notify_key = f"{day_key}:{p}"
            if notify_key in self._notified_keys:
                continue
            # If current time is within trigger window, notify once.
            if trigger <= now < (trigger + datetime.timedelta(seconds=grace_seconds)):
                self._notify(p, target.strftime("%H:%M"))
                self._notified_keys.add(notify_key)

    def _deliver_notification(self, prayer, message, title):
        # Speech is primary channel for automatic reminders.
        try:
            self._handle_message(f"notify:{prayer}", message)
        except Exception:
            try:
                log.exception("Muslimku: failed to deliver reminder speech via _handle_message.")
            except Exception:
                pass
            try:
                ui.message(message)
            except Exception:
                try:
                    log.exception("Muslimku: failed to deliver reminder speech via ui.message fallback.")
                except Exception:
                    pass

        # Visual notification is optional and non-blocking.
        try:
            # Prefer OS-level toast notification for taskbar/Notification Center behavior.
            notif = wx.adv.NotificationMessage(title=title, message=message)
            try:
                notif.SetFlags(wx.ICON_INFORMATION)
            except Exception:
                pass
            notif.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
        except Exception:
            try:
                if hasattr(gui, "notification"):
                    gui.notification(message)
            except Exception:
                try:
                    log.exception("Muslimku: failed to show optional reminder notification.")
                except Exception:
                    pass

    def _notify(self, prayer, time_str):
        try:
            lang = config.conf["muslimku"].get("language", "en")
            city = config.conf["muslimku"].get("city", "")
            if lang == "id":
                nama = {
                    "Fajr": "Subuh",
                    "Dhuhr": "Dzuhur",
                    "Asr": "Ashar",
                    "Maghrib": "Maghrib",
                    "Isha": "Isya"
                }.get(prayer, prayer)
                # Indonesian notification with region mention
                message = (
                    f"Waktu {nama} telah tiba, untuk Wilayah {city} dan Sekitarnya! "
                    f"Mari tinggalkan komputer sejenak, lalu tunaikan Solat {nama}."
                )
                title = f"Waktu {nama}"
            else:
                message = f"Reminder: {prayer} at {time_str}."
                title = f"{prayer} reminder"
            # Ensure delivery runs on NVDA main/UI thread.
            try:
                wx.CallAfter(self._deliver_notification, prayer, message, title)
            except Exception:
                self._deliver_notification(prayer, message, title)
        except Exception:
            try:
                log.exception("Muslimku: unexpected error while preparing reminder notification.")
            except Exception:
                pass

    def _get_location_now(self, resp_data):
        tz_name = None
        try:
            tz_name = resp_data.get("meta", {}).get("timezone")
        except Exception:
            tz_name = None
        if tz_name and ZoneInfo:
            try:
                return datetime.datetime.now(ZoneInfo(tz_name))
            except Exception:
                try:
                    log.debug(f"Muslimku: failed to load timezone '{tz_name}', using local timezone.")
                except Exception:
                    pass
        return datetime.datetime.now().astimezone()

    def _get_calc_method(self):
        try:
            return int(config.conf["muslimku"].get("calculation_method", 11))
        except Exception:
            return 11

    def _get_calc_method_settings(self, method_id):
        # Aladhan method settings for Muhammadiyah profile.
        if int(method_id) == 99:
            return MUHAMMADIYAH_METHOD_SETTINGS
        return None

    def _get_madhab_school(self):
        try:
            madhab = str(config.conf["muslimku"].get("madhab", "shafi")).lower()
        except Exception:
            madhab = "shafi"
        # Aladhan school: 0 = Shafi, 1 = Hanafi
        return 1 if madhab == "hanafi" else 0

    def _get_prayer_offset_minutes(self, prayer_key):
        return int(FIXED_PRAYER_OFFSETS.get(prayer_key, 0))

    def _parse_api_time_to_datetime(self, time_str, base_now):
        if not time_str:
            return None
        tpart = str(time_str).split()[0]
        try:
            hour, minute = [int(x) for x in tpart.split(":")]
        except Exception:
            return None
        return datetime.datetime(
            base_now.year, base_now.month, base_now.day, hour, minute, tzinfo=base_now.tzinfo
        )

    def _get_adjusted_prayer_datetime(self, timings, prayer_key, base_now):
        raw = timings.get(prayer_key)
        dt = self._parse_api_time_to_datetime(raw, base_now)
        if not dt:
            return None
        delta = self._get_prayer_offset_minutes(prayer_key)
        return dt + datetime.timedelta(minutes=delta)

    def _fetch_timings(self, date_str=None, timeout=10):
        base_url = "https://api.aladhan.com/v1/timingsByCity"
        if date_str:
            base_url = f"{base_url}/{date_str}"
        method_id = self._get_calc_method()
        params = {
            "city": config.conf["muslimku"]["city"],
            "country": config.conf["muslimku"]["country"],
            "method": method_id,
            "school": self._get_madhab_school()
        }
        method_settings = self._get_calc_method_settings(method_id)
        if method_settings:
            params["methodSettings"] = method_settings
        return requests.get(
            base_url,
            params=params,
            timeout=timeout
        )

    def _get_cached_hijri_for_date(self, target_date, cache_seconds=21600, timeout=3):
        try:
            key = target_date.strftime("%Y-%m-%d")
            now_ts = time.time()
            cache = getattr(self, "_hijri_cache", {})
            entry = cache.get(key)
            if entry and (now_ts - float(entry.get("ts", 0.0)) < cache_seconds):
                return entry.get("hijri")

            resp = self._fetch_timings(
                date_str=target_date.strftime("%d-%m-%Y"),
                timeout=timeout
            )
            hijri = resp.json().get("data", {}).get("date", {}).get("hijri")
            if hijri:
                cache[key] = {"ts": now_ts, "hijri": hijri}
                self._hijri_cache = cache
            return hijri
        except Exception:
            return None

    def _copy_to_clipboard(self, text):
        try:
            if not text:
                return False
            # Use wx clipboard
            if wx.TheClipboard.Open():
                try:
                    data = wx.TextDataObject()
                    data.SetText(text)
                    wx.TheClipboard.SetData(data)
                    return True
                finally:
                    wx.TheClipboard.Close()
        except Exception:
            try:
                # Fallback: try wx on newer API
                cb = wx.Clipboard.Get()
                cb.SetData(wx.TextDataObject(text))
                return True
            except Exception:
                return False

    def _post_ui_message(self, message):
        try:
            wx.CallAfter(ui.message, message)
        except Exception:
            ui.message(message)

    def _handle_message(self, key, message):
        try:
            if not wx.IsMainThread():
                wx.CallAfter(self._handle_message, key, message)
                return
        except Exception:
            pass

        now = time.time()
        last = self._last_invoke.get(key)
        if last and (now - last.get("ts", 0) <= self._double_threshold):
            # double-press detected: copy last message to clipboard
            text_to_copy = last.get("msg") or message
            copied = self._copy_to_clipboard(text_to_copy)
            lang = config.conf["muslimku"].get("language", "en")
            if lang == "id":
                confirm = "Teks hasil disalin ke clipboard."
            else:
                confirm = "Result copied to clipboard."
            if copied:
                ui.message(confirm)
            else:
                ui.message("Failed to copy to clipboard.")
            # reset last to avoid repeated copies on subsequent presses
            self._last_invoke.pop(key, None)
            return

        # not a double-press: show message and record it
        ui.message(message)
        self._last_invoke[key] = {"ts": now, "msg": message}

    @scriptHandler.script(description=GESTURE_DESC["fajr"], gesture="kb:NVDA+control+shift+1", category=UI_GESTURE_CATEGORY)
    def script_subuh(self, gesture):
        self.announce_prayer("Fajr")

    @scriptHandler.script(description=GESTURE_DESC["dhuhr"], gesture="kb:NVDA+control+shift+2", category=UI_GESTURE_CATEGORY)
    def script_dzuhur(self, gesture):
        self.announce_prayer("Dhuhr")

    @scriptHandler.script(description=GESTURE_DESC["asr"], gesture="kb:NVDA+control+shift+3", category=UI_GESTURE_CATEGORY)
    def script_ashar(self, gesture):
        self.announce_prayer("Asr")

    @scriptHandler.script(description=GESTURE_DESC["maghrib"], gesture="kb:NVDA+control+shift+4", category=UI_GESTURE_CATEGORY)
    def script_maghrib(self, gesture):
        self.announce_prayer("Maghrib")

    @scriptHandler.script(description=GESTURE_DESC["isha"], gesture="kb:NVDA+control+shift+5", category=UI_GESTURE_CATEGORY)
    def script_isya(self, gesture):
        self.announce_prayer("Isha")

    @scriptHandler.script(description=GESTURE_DESC["next_prayer"], gesture="kb:NVDA+control+shift+w", category=UI_GESTURE_CATEGORY)
    def script_next_prayer(self, gesture):
        self.announce_next_prayer()

    @scriptHandler.script(description=GESTURE_DESC["location"], gesture="kb:NVDA+control+shift+l", category=UI_GESTURE_CATEGORY)
    def script_location(self, gesture):
        self.announce_location()

    @scriptHandler.script(description=GESTURE_DESC["qibla"], gesture="kb:NVDA+control+shift+q", category=UI_GESTURE_CATEGORY)
    def script_qibla(self, gesture):
        with self._qibla_lock:
            if self._qibla_busy:
                lang = config.conf["muslimku"].get("language", "en")
                msg = (
                    "Pemeriksaan Qiblat dari lokasi Anda, dalam proses."
                    if lang == "id"
                    else "Checking the Qibla from your location: in progress."
                )
                self._beep()
                self._handle_message("qibla:progress", msg)
                return
            self._qibla_busy = True

        lang = config.conf["muslimku"].get("language", "en")
        progress_msg = (
            "Pemeriksaan Qiblat dari lokasi Anda, dalam proses."
            if lang == "id"
            else "Checking the Qibla from your location: in progress."
        )
        self._beep()
        self._handle_message("qibla:progress", progress_msg)
        threading.Thread(target=self._compute_qibla_async, daemon=True).start()

    def announce_time(self, api_key, name_en, name_id):
        def worker():
            try:
                payload = self._get_cached_timings_payload()
                if not payload:
                    self._post_ui_message("Failed to retrieve prayer time.")
                    return

                data = payload.get("timings", {})
                now_loc = self._get_location_now(payload)
                time_str = data.get(api_key)
                if api_key in FIXED_PRAYER_OFFSETS:
                    adjusted = self._get_adjusted_prayer_datetime(data, api_key, now_loc)
                    if adjusted:
                        time_str = adjusted.strftime("%H:%M")
                # Some APIs don't provide 'Dhuha' directly. Compute it from Sunrise if needed.
                if not time_str and api_key == "Dhuha":
                    try:
                        sunrise = data.get("Sunrise")
                        if sunrise:
                            sunrise_dt = self._parse_api_time_to_datetime(sunrise, now_loc)
                            if sunrise_dt:
                                # Default Dhuha: 60 minutes after sunrise
                                dhuha_dt = sunrise_dt + datetime.timedelta(minutes=60)
                                time_str = dhuha_dt.strftime("%H:%M")
                    except Exception:
                        time_str = None
                if not time_str:
                    return

                lang = config.conf["muslimku"].get("language", "en")
                if lang == "id":
                    message = f"Waktu {name_id} hari ini adalah pukul {time_str}."
                else:
                    message = f"{name_en} time today: {time_str}."
                wx.CallAfter(self._handle_message, f"time:{api_key}", message)
            except Exception:
                self._post_ui_message("Failed to retrieve prayer time.")

        threading.Thread(target=worker, daemon=True).start()

    @scriptHandler.script(description=GESTURE_DESC["imsak"], gesture="kb:NVDA+control+shift+6", category=UI_GESTURE_CATEGORY)
    def script_imsak(self, gesture):
        self.announce_time("Imsak", "Imsak", "Imsak")

    @scriptHandler.script(description=GESTURE_DESC["sunrise"], gesture="kb:NVDA+control+shift+7", category=UI_GESTURE_CATEGORY)
    def script_sunrise(self, gesture):
        self.announce_time("Sunrise", "Sunrise", "Terbit Fajar")

    @scriptHandler.script(description=GESTURE_DESC["dhuha"], gesture="kb:NVDA+control+shift+8", category=UI_GESTURE_CATEGORY)
    def script_dhuha_time(self, gesture):
        self.announce_time("Dhuha", "Dhuha", "Dhuha")

    @scriptHandler.script(description=GESTURE_DESC["sunset"], gesture="kb:NVDA+control+shift+9", category=UI_GESTURE_CATEGORY)
    def script_sunset(self, gesture):
        # "Sunset" is the API key for sunset/terbenam
        self.announce_time("Sunset", "Sunset", "Matahari terbenam")

    # test notification script removed per user request

    @scriptHandler.script(description=GESTURE_DESC["hari"], gesture="kb:NVDA+control+shift+h", category=UI_GESTURE_CATEGORY)
    def script_hari(self, gesture):
        threading.Thread(target=self._announce_day_info_worker, daemon=True).start()

    def _announce_day_info_worker(self):
        try:
            resp_data = self._get_cached_timings_payload()
            if not resp_data:
                self._post_ui_message("Failed to retrieve calendar data.")
                return
            timings = resp_data.get("timings", {})
            date_info = resp_data.get("date", {})
            hijri = date_info.get("hijri", {})
            greg = date_info.get("gregorian", {})
            now_loc = self._get_location_now(resp_data)

            hijri_day = hijri.get("day")
            hijri_year = hijri.get("year")
            hijri_month_number = int(hijri.get("month", {}).get("number", 1))

            # If local time is past Maghrib for the configured location, advance Hijri day
            try:
                maghrib_str = timings.get("Maghrib")
                if maghrib_str:
                    mag_t = maghrib_str.split()[0]
                    mh, mm = [int(x) for x in mag_t.split(":")]
                    mag_dt = datetime.datetime(now_loc.year, now_loc.month, now_loc.day, mh, mm, tzinfo=now_loc.tzinfo)
                    if now_loc >= mag_dt:
                        # try to fetch tomorrow's hijri date
                        try:
                            tomorrow = now_loc + datetime.timedelta(days=1)
                            hijri2 = self._get_cached_hijri_for_date(tomorrow, timeout=3)
                            if hijri2:
                                hijri_day = hijri2.get("day")
                                hijri_year = hijri2.get("year")
                                hijri_month_number = int(hijri2.get("month", {}).get("number", hijri_month_number))
                        except Exception:
                            # fallback: naive increment
                            try:
                                hd = int(hijri_day)
                                hd += 1
                                if hd > 30:
                                    hd = 1
                                    hijri_month_number = (hijri_month_number % 12) + 1
                                    hijri_year = str(int(hijri_year) + 1)
                                hijri_day = str(hd)
                            except Exception:
                                pass
            except Exception:
                pass

            # Mapping bulan Hijriyah berdasarkan nomor (bukan string API)
            hijri_month_map_id = {
                1: "Muharram",
                2: "Safar",
                3: "Rabiul Awal",
                4: "Rabiul Akhir",
                5: "Jumadil Awal",
                6: "Jumadil Akhir",
                7: "Rajab",
                8: "Sya'ban",
                9: "Ramadan",
                10: "Syawal",
                11: "Zulkaidah",
                12: "Zulhijah"
            }

            hijri_month_id = hijri_month_map_id.get(
                hijri_month_number,
                hijri["month"]["en"]
            )

            greg_day = greg["day"]
            greg_month = greg["month"]["en"]
            greg_year = greg["year"]
            weekday_en = greg["weekday"]["en"]

            hari_map = {
                "Monday": "Senin",
                "Tuesday": "Selasa",
                "Wednesday": "Rabu",
                "Thursday": "Kamis",
                "Friday": "Jumat",
                "Saturday": "Sabtu",
                "Sunday": "Minggu"
            }

            bulan_map = {
                "January": "Januari",
                "February": "Februari",
                "March": "Maret",
                "April": "April",
                "May": "Mei",
                "June": "Juni",
                "July": "Juli",
                "August": "Agustus",
                "September": "September",
                "October": "Oktober",
                "November": "November",
                "December": "Desember"
            }

            date_obj = datetime.datetime(
                int(greg_year),
                int(greg["month"]["number"]),
                int(greg_day)
            )

            base_date = datetime.datetime(2024, 1, 1)
            selisih = (date_obj - base_date).days
            pasaran_list = ["Legi", "Pahing", "Pon", "Wage", "Kliwon"]
            pasaran = pasaran_list[selisih % 5]

            lang = config.conf["muslimku"]["language"]
            country = config.conf["muslimku"].get("country", "")

            # Only include Javanese pasaran when country is Indonesia
            include_pasaran = (country == "Indonesia")

            if lang == "id":
                # Indonesian message: include pasaran only for Indonesia
                if include_pasaran:
                    message = (
                        f"{hari_map.get(weekday_en, weekday_en)} {pasaran}, "
                        f"{hijri_day} {hijri_month_id} {hijri_year} Hijriyah/"
                        f"{greg_day} {bulan_map.get(greg_month, greg_month)} {greg_year} Miladiyah."
                    )
                else:
                    message = (
                        f"{hari_map.get(weekday_en, weekday_en)}, "
                        f"{hijri_day} {hijri_month_id} {hijri_year} Hijriyah/"
                        f"{greg_day} {bulan_map.get(greg_month, greg_month)} {greg_year} Miladiyah."
                    )
            else:
                # English message: append pasaran note only for Indonesia
                if include_pasaran:
                    message = (
                        f"{weekday_en}, "
                        f"{hijri_day} {hijri['month']['en']} {hijri_year} AH/"
                        f"{greg_day} {greg_month} {greg_year} AD. Pasaran: {pasaran}"
                    )
                else:
                    message = (
                        f"{weekday_en}, "
                        f"{hijri_day} {hijri['month']['en']} {hijri_year} AH/"
                        f"{greg_day} {greg_month} {greg_year} AD."
                    )

            wx.CallAfter(self._handle_message, "hari", message)
        except Exception:
            self._post_ui_message("Failed to retrieve calendar data.")

    def announce_prayer(self, prayer):
        def worker():
            try:
                payload = self._get_cached_timings_payload()
                if not payload:
                    self._post_ui_message("Failed to retrieve prayer time.")
                    return
                data = payload.get("timings", {})
                now_loc = self._get_location_now(payload)
                target = self._get_adjusted_prayer_datetime(data, prayer, now_loc)
                if not target:
                    return
                time_str = target.strftime("%H:%M")

                lang = config.conf["muslimku"]["language"]

                if lang == "id":
                    nama = {
                        "Fajr": "Subuh",
                        "Dhuhr": "Dzuhur",
                        "Asr": "Ashar",
                        "Maghrib": "Maghrib",
                        "Isha": "Isya"
                    }.get(prayer, prayer)

                    message = f"Waktu {nama} hari ini: pukul {time_str}."
                else:
                    message = f"{prayer} time today: {time_str}."

                wx.CallAfter(self._handle_message, f"prayer:{prayer}", message)
            except Exception:
                self._post_ui_message("Failed to retrieve prayer time.")

        threading.Thread(target=worker, daemon=True).start()

    def announce_next_prayer(self):
        def worker():
            try:
                payload = self._get_cached_timings_payload()
                if not payload:
                    self._post_ui_message("Failed to retrieve prayer time.")
                    return
                data = payload.get("timings", {})
                now = self._get_location_now(payload)

                prayers = [
                    ("Fajr", "Subuh", "Fajr"),
                    ("Dhuhr", "Dzuhur", "Dhuhr"),
                    ("Asr", "Ashar", "Asr"),
                    ("Maghrib", "Maghrib", "Maghrib"),
                    ("Isha", "Isya", "Isha")
                ]

                next_prayer = None
                next_time = None
                for api_key, id_name, en_name in prayers:
                    candidate = self._get_adjusted_prayer_datetime(data, api_key, now)
                    if not candidate:
                        continue
                    if candidate > now:
                        next_prayer = (api_key, id_name, en_name)
                        next_time = candidate
                        break

                # If all daily prayers have passed, next is tomorrow's Fajr.
                if not next_prayer:
                    fajr = self._get_adjusted_prayer_datetime(data, "Fajr", now)
                    if not fajr:
                        return
                    next_prayer = ("Fajr", "Subuh", "Fajr")
                    next_time = fajr + datetime.timedelta(days=1)

                remaining = next_time - now
                total_minutes = int(max(0, remaining.total_seconds()) // 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60

                lang = config.conf["muslimku"].get("language", "en")
                if lang == "id":
                    message = (
                        f"Menuju waktu solat berikutnya adalah Solat {next_prayer[1]}: "
                        f"Dalam {hours} jam, dan {minutes} menit lagi."
                    )
                else:
                    message = (
                        f"Next prayer is {next_prayer[2]}: "
                        f"In {hours} hours and {minutes} minutes."
                    )

                wx.CallAfter(self._handle_message, "next_prayer", message)
            except Exception:
                self._post_ui_message("Failed to retrieve prayer time.")

        threading.Thread(target=worker, daemon=True).start()

    def announce_location(self):
        try:
            lang = config.conf["muslimku"].get("language", "en")
            country = config.conf["muslimku"].get("country", "")
            city = (config.conf["muslimku"].get("city", "") or "").strip()
            province = (config.conf["muslimku"].get("province", "") or "").strip()
            regency = (config.conf["muslimku"].get("regency", "") or "").strip()

            if country == INDONESIA_COUNTRY and regency and province:
                if lang == "id":
                    message = f"Lokasi Anda saat ini: {regency}, Provinsi {province}, {country}."
                else:
                    reg_name = regency
                    up = reg_name.upper()
                    if up.startswith("KABUPATEN "):
                        reg_name = f"{reg_name[10:].strip().title()} Regency"
                    elif up.startswith("KOTA "):
                        reg_name = f"{reg_name[5:].strip().title()} City"
                    message = f"Your current location is: {reg_name}, {province} Province, {country}."
            else:
                if lang == "id":
                    if city and country:
                        message = f"Lokasi Anda saat ini: {city}, {country}."
                    elif city:
                        message = f"Lokasi Anda saat ini: {city}."
                    else:
                        message = "Lokasi belum diatur."
                else:
                    if city and country:
                        message = f"Your current location is: {city}, {country}."
                    elif city:
                        message = f"Your current location is: {city}."
                    else:
                        message = "Location is not set yet."

            self._handle_message("location", message)
        except Exception:
            ui.message("Failed to announce location.")

    def _beep(self):
        try:
            if tones:
                tones.beep(880, 90)
            else:
                wx.Bell()
        except Exception:
            pass

    def _compute_qibla_async(self):
        try:
            lang = config.conf["muslimku"].get("language", "en")
            country = (config.conf["muslimku"].get("country", "") or "").strip()
            city = (config.conf["muslimku"].get("city", "") or "").strip()
            province = (config.conf["muslimku"].get("province", "") or "").strip()
            regency = (config.conf["muslimku"].get("regency", "") or "").strip()

            query_parts = []
            if country == INDONESIA_COUNTRY and regency:
                query_parts.append(regency)
            elif city:
                query_parts.append(city)
            if province:
                query_parts.append(province)
            if country:
                query_parts.append(country)
            query = ", ".join([x for x in query_parts if x])

            if not query:
                msg = "Lokasi belum diatur." if lang == "id" else "Location is not set yet."
                wx.CallAfter(self._finish_qibla, msg)
                return

            try:
                response = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": query, "format": "jsonv2", "limit": 1},
                    headers={"User-Agent": "muslimku-nvda-addon/1.0"},
                    timeout=10
                )
                response.raise_for_status()
                results = response.json()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                msg = (
                    "Tidak ada koneksi Internet. Hubungkan ke Internet dan coba lagi."
                    if lang == "id"
                    else "No Internet connection. Connect to the Internet first and try again."
                )
                wx.CallAfter(self._finish_qibla, msg)
                return

            if not results:
                msg = (
                    "Lokasi tidak ditemukan. Periksa pengaturan lokasi Anda."
                    if lang == "id"
                    else "Location not found. Please check your location settings."
                )
                wx.CallAfter(self._finish_qibla, msg)
                return

            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            deg = int(round(self._calculate_qibla_bearing(lat, lon)))
            dir_id, dir_en = self._direction_label_8(deg)
            msg = (
                f"Qiblat Diperoleh! Arah kiblat dari lokasi Anda adalah {deg} derajat ({dir_id})."
                if lang == "id"
                else f"Qibla Detected! Qibla direction from your location is {deg} degrees ({dir_en})."
            )
            wx.CallAfter(self._finish_qibla, msg)
        except Exception:
            try:
                log.exception("Muslimku: unexpected error while checking Qibla.")
            except Exception:
                pass
            lang = config.conf["muslimku"].get("language", "en")
            msg = (
                "Gagal memeriksa arah kiblat. Coba lagi."
                if lang == "id"
                else "Failed to check Qibla direction. Please try again."
            )
            wx.CallAfter(self._finish_qibla, msg)

    def _finish_qibla(self, message):
        try:
            self._beep()
            self._handle_message("qibla:result", message)
        finally:
            with self._qibla_lock:
                self._qibla_busy = False

    def _calculate_qibla_bearing(self, lat_deg, lon_deg):
        kaaba_lat = math.radians(21.4225)
        kaaba_lon = math.radians(39.8262)
        lat = math.radians(lat_deg)
        lon = math.radians(lon_deg)
        dlon = kaaba_lon - lon
        x = math.sin(dlon)
        y = (math.cos(lat) * math.tan(kaaba_lat)) - (math.sin(lat) * math.cos(dlon))
        brng = math.degrees(math.atan2(x, y))
        return (brng + 360.0) % 360.0

    def _direction_label_8(self, bearing):
        dirs_id = ["utara", "timur laut", "timur", "tenggara", "selatan", "barat daya", "barat", "barat laut"]
        dirs_en = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
        idx = int((bearing + 22.5) // 45) % 8
        return dirs_id[idx], dirs_en[idx]
