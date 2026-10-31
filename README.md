# KrishiRakshak 2.0 🌾

India-wide agricultural assistance **prototype** built with FastAPI, SQLite, HTML/CSS/JS, Leaflet and Open-Meteo. This release hardens the authentication/location foundation; it does not claim that every planned agricultural integration is complete.

## Included in this build
- Farmer email/password registration and login; passwords are hashed.
- Signed, HTTP-only session cookie (replaces the old editable farmer-ID cookie).
- Farmer profile and farm-plot records stored in SQLite.
- All 22 scheduled-language names available as options; actual translation is not yet connected.
- Browser GPS request and draggable/clickable map marker.
- Separate in-app consent required before farm coordinates are saved; saved coordinates can be deleted.
- Location updates no longer overwrite unrelated profile fields such as phone, language or land unit.
- Basic land-unit converter with explicitly approximate regional units.
- Live Open-Meteo forecast when the external service is reachable.
- Preliminary rule-based crop shortlist and indicative input estimates (not validated agronomy advice).
- Task reminders stored in the application (no SMS/push/email delivery yet).
- Crop-photo upload with image type/signature and size checks; no AI diagnosis model is connected.
- Mandi price endpoint returns clearly labelled illustrative demo rows, not live prices.
- Static flood preparedness/recovery guidance and links to official alert sources; no live CWC/IMD warning feed.

## Important limitations
This is a development MVP, **not a production-ready or certified farm-advisory system**.
- Google OAuth and phone OTP are not implemented.
- Bhashini translation/speech needs approved credentials and a real pipeline adapter. Selecting a language does not yet translate the interface.
- District-specific land conversion definitions need authoritative state/revenue-record data; approximate constants must not be used for legal measurement.
- Crop recommendations, crop duration, seed/fertilizer quantities and water estimates are simplified placeholders. Confirm with ICAR/state agricultural university/KVK and soil-test recommendations.
- Irrigation scheduling is not yet crop-stage/soil-moisture aware.
- Crop photo upload does not identify disease; do not use it to choose pesticides.
- Mandi rows are demo data until an exact AGMARKNET/data.gov.in resource is configured and verified.
- Flood content is guidance only, not a live alert service. Use official warnings and emergency instructions.
- Reminders are in-app records only; no background scheduler or notifications are configured.

## Run locally (Windows)
1. Install Python 3.10+.
2. Open this folder in VS Code or PowerShell.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and set a long random `APP_SECRET`.
6. Start the server:
   ```powershell
   uvicorn main:app --reload
   ```
7. Open http://127.0.0.1:8000

## Run on macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set APP_SECRET
uvicorn main:app --reload
```

For HTTPS deployment set `APP_ENV=production`, a strong unique `APP_SECRET`, and `COOKIE_SECURE=true`. Do not use the development defaults in production.

## Official data integration roadmap
- Weather: [Open-Meteo](https://open-meteo.com/) forecast API (forecast, not official warning).
- Market prices: [AGMARKNET](https://agmarknet.gov.in/) / [data.gov.in](https://data.gov.in/); configure and validate the exact resource and API key server-side.
- Crop practices and varieties: ICAR, state agriculture universities, KVKs and state agriculture department advisories.
- Soil: Soil Health Card / verified laboratory report entered by farmer.
- Flood: [Central Water Commission Flood Forecasting](https://ffs.india-water.gov.in/), IMD and state disaster-management authorities.
- Maps: OpenStreetMap tiles via Leaflet.
- Language: [Bhashini](https://bhashini.gov.in/) approved translation/speech services.
- Disease model: research datasets such as PlantVillage require field-image validation and agronomist review before deployment.

## Security work still required before deployment
- Add CSRF protection and login/register rate limiting.
- Add email verification, password reset and real OTP/OAuth flows if required.
- Configure HTTPS, strong secret, secure cookie flag, backups and production database.
- Add privacy notice, data-retention policy, consent audit and account/data deletion workflow.
- Run dependency, integration, authorization and penetration tests.

## Version 2.0 changes
- Replaced the unsigned `kr_user` cookie with Starlette's signed session cookie.
- Added a production guard against the default application secret.
- Fixed profile/location updates so they only modify submitted fields.
- Added explicit location-saving consent and a delete-location action.
- Added coordinate range checks and basic upload file-signature validation.
- Expanded `/api/health` to report prototype/integration status honestly.
