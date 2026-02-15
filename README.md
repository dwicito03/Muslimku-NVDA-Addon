# Muslimku NVDA Add-on

Version: **7.1.1**

Muslimku is an NVDA add-on for prayer time announcements, Hijri/Gregorian date announcements, Qibla direction checking, and reminder notifications based on the selected location.

## Features

- Announces the five daily prayer times: Fajr, Dhuhr, Asr, Maghrib, and Isha.
- Announces additional times: Imsak, Sunrise, Dhuha, and Sunset.
- Announces the next prayer and remaining time (hours and minutes).
- Announces current configured location.
- Checks and announces Qibla direction in degrees and cardinal direction.
- Announces Hijri/Gregorian date with Maghrib-based Hijri date transition.
- Provides automatic prayer reminders with configurable minute offset.
- Supports calculation method selection for prayer time calculation.
- Supports Asr madhab selection (Shafi/Hanafi).
- Supports prayer time calculation methods based on recognized institutions.
- Uses speech-first reminder delivery with optional Windows toast notification.
- Supports Indonesian and English for settings and announcement messages.
- Supports double-press behavior to copy announced text to clipboard.
- Allows all gestures to be customized from NVDA Input Gestures.

## Location Settings

Open NVDA > Preferences > Settings > Muslimku.

- `Country = Indonesia`:
  - Location uses `Province` and `City/Regency` combo boxes.
- `Country != Indonesia`:
  - Location uses a `City` combo box list for the selected country.

Additional settings:

- Language: `Indonesia` or `English`.
- Calculation method: selectable prayer calculation method.
- Asr madhab: `Shafi` or `Hanafi`.
- Enable reminders: on/off.
- Reminder offset (minutes): reminder trigger before prayer time.

## Default Shortcuts

All commands are under the `Muslimku` category in NVDA Input Gestures.

- `NVDA+Ctrl+Shift+1`: Announce Fajr time.
- `NVDA+Ctrl+Shift+2`: Announce Dhuhr time.
- `NVDA+Ctrl+Shift+3`: Announce Asr time.
- `NVDA+Ctrl+Shift+4`: Announce Maghrib time.
- `NVDA+Ctrl+Shift+5`: Announce Isha time.
- `NVDA+Ctrl+Shift+6`: Announce Imsak time.
- `NVDA+Ctrl+Shift+7`: Announce Sunrise time.
- `NVDA+Ctrl+Shift+8`: Announce Dhuha time.
- `NVDA+Ctrl+Shift+9`: Announce Sunset time.
- `NVDA+Ctrl+Shift+H`: Announce Hijri and Gregorian date.
- `NVDA+Ctrl+Shift+W`: Announce next prayer.
- `NVDA+Ctrl+Shift+L`: Announce current location.
- `NVDA+Ctrl+Shift+Q`: Check Qibla direction.

## Installation

1. Download the `.nvda-addon` package.
2. Open NVDA > Tools > Manage add-ons > Install.
3. Select the add-on file.
4. Restart NVDA if prompted.

## Customizing Shortcuts

1. Open NVDA > Preferences > Input Gestures.
2. Select category `Muslimku`.
3. Select command.
4. Click `Change`, press the new key combination, then confirm.

## Technical Notes

- Prayer time and Hijri date source: Aladhan API (`https://api.aladhan.com`).
- Indonesia province/regency source: Emsifa Indonesia region API (`https://www.emsifa.com/api-wilayah-indonesia/`).
- Global city list source for non-Indonesia countries: CountriesNow API (`https://countriesnow.space/`).
- Qibla coordinate lookup uses OpenStreetMap Nominatim (`https://nominatim.openstreetmap.org/`).
- Prayer time calculations follow the selected institutional method and madhab settings.
- Internet connection is required for online location/time services.

## License

MIT

## Contact

- Email: `surel@dwicito.com`
- Website: `https://dwicito.com`
