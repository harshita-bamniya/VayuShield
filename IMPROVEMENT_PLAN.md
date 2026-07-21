# VayuShield AI — Improvement Plan (61% → 90%)

**Hackathon:** ET AI Hackathon 2026 · Problem Statement 5  
**Date created:** 2026-07-17  
**Current score:** ~84% | **Target:** 90% | **Gap:** +6%  
**Last updated:** 2026-07-17 | Items 03, 04, 05, 06, 08, 09, 10 complete

---

## Phase 1 — Quick Wins (+13%, ~10 hrs)

### 01. Architecture Diagram [+5%, ~2 hrs] — NON-CODE
- Draw data flow: WAQI/CPCB/FIRMS/Open-Meteo → Ingestion → PostgreSQL+PostGIS → Attribution/Forecasting/Enforcement/Advisory → React frontend
- Include: API key sources, PostGIS spatial queries, Groq/LLaMA call, 30-min poller, background task lifecycle
- Tools: draw.io, Excalidraw, or Miro
- Output: `docs/architecture.png` + `docs/architecture.pdf`
- Reference in README.md

### 02. Presentation Deck [+5%, ~4 hrs] — NON-CODE
- Slide 1: Problem — 900+ CAAQMS sensors, data unacted upon, AQI breaches cost lives
- Slide 2: Solution — source attribution → 72h forecast → ranked enforcement → citizen advisories
- Slides 3–5: Screenshots of Dashboard, WardDetail, Enforcement queue, Compare page
- Slide 6: Tech stack & differentiators (ward-hyperlocal-v1, OSM source discovery, multilingual IVR)
- Slide 7: Real-world impact — wards covered, cities, enforcement actions
- Output: `docs/presentation.pptx` + `docs/presentation.pdf`

### 03. Population Vulnerability Scoring [+3%, ~3 hrs] — ✅ IMPLEMENTED
- Ward `vulnerability_score` column exists but is NULL everywhere
- Formula: `score = (population_density × 0.4) + (avg_aqi/500 × 0.6)` normalized 0–1
- Backend: `compute_vulnerability_scores(db, city_id)` in `cities/service.py`
- Trigger: called from `_refresh_city()` in `main.py` after attribution
- Frontend: vulnerability badge (Critical/High/Moderate/Low) on `WardDetail.tsx`
- Files changed:
  - `backend/app/modules/cities/service.py` — add compute function
  - `backend/app/main.py` — call it in _refresh_city
  - `frontend/src/pages/WardDetail.tsx` — show vulnerability badge

### 04. WhatsApp Alert Delivery Connector [+3%, ~4 hrs] — ✅ IMPLEMENTED
- Config key `WHATSAPP_ENABLED` exists; advisories stored in DB but never sent
- New file: `backend/app/modules/advisory/connectors/whatsapp.py`
- Function: `send_whatsapp_advisory(phone, text, lang)` via Twilio API
- Config: add `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` to `config.py`
- Hook into `advisory/service.py` after saving advisory to DB
- Frontend: show "WhatsApp ✓ / IVR ✓" delivery status in `Advisories.tsx`

---

## Phase 2 — High Impact Features (+13%, ~16 hrs)

### 05. NASA MODIS Satellite AOD Layer [+7%, ~8 hrs] — ✅ IMPLEMENTED
- Connector: `backend/app/modules/ingestion/connectors/satellite.py` — NASA LAADS DAAC + Giovanni; mock fallback with deterministic city AOD baseline
- Migration: `0017_satellite_observations.py` (city_id, observed_date, aod_value, estimated_pm25, source, is_mock)
- API: `GET /cities/{city_id}/satellite` + `POST .../satellite/poll`; auto-called in `_refresh_city()`
- Config: `EARTHDATA_TOKEN` added to `config.py`
- Frontend: NASA GIBS `WMSTileLayer` toggle on `WardMap.tsx`; "Satellite vs Ground" card on Dashboard with AOD, est. PM2.5, bias column, 7-day mini bar chart

### 06. Traffic / Mobility Feed Integration [+5%, ~8 hrs] — ✅ IMPLEMENTED
- Connector: `backend/app/modules/ingestion/connectors/traffic.py` — TomTom Flow API; named segments per city (Delhi/Mumbai/Bengaluru + generic fallback); mock via deterministic peak-hour model
- Migration: `0018_traffic_snapshots.py` (city_id, ts, segment_id, congestion_ratio, current_speed, free_flow_speed, lat, lon, is_mock)
- API: `GET /cities/{city_id}/traffic` + `POST .../traffic/poll`; auto-wired into `_refresh_city()`
- Config: `TOMTOM_API_KEY` added to `config.py`
- Attribution boost: `get_avg_congestion_ratio()` called in `attribution/service.py` between steps 5 and 6; if avg > 1.5, vehicular fingerprint boosted by up to +15% (proportional to congestion level)
- Frontend `WardMap.tsx`: `showTraffic` prop + `CircleMarker` per segment coloured green→lime→orange→red by ratio; popup shows speed/ratio/label
- Frontend `Dashboard.tsx`: "🚗 Traffic" toggle button on map; full congestion panel with per-segment progress bars + "vehicular attribution boosted by N%" notice when congestion is active

### 07. Demo Video [+4%, ~3 hrs] — NON-CODE
- Script: Login → Dashboard → ward click → WardDetail → Enforcement → Advisory → Compare
- Show "Discover Sources" working live for non-Delhi city
- Record with OBS Studio (free) at 1080p with voice-over
- Upload to YouTube (unlisted), embed link in README and deck

### 08. Intervention Effectiveness UI [+2%, ~4 hrs] — ✅ IMPLEMENTED
- Backend already computes `intervention_effectiveness` ratio in `compare.py`
- `ComparePage.tsx`: effectiveness table already present (was complete)
- `Enforcement.tsx`: added 4-column summary banner (Pending/Dispatched/Completed + completion rate bar)
- `ReportsPage.tsx`: added `EnforcementStatCard` — "Interventions Completed (Nd)" with rate bar
- Backend: `get_enforcement_stats()` in `reports/repository.py`; `EnforcementStats` schema; wired into `service.py`

---

## Phase 3 — Polish & Security (+3%, ~4 hrs)

### 09. Fix Default JWT Secret + Rate Limiting [+2%, ~1 hr] — ✅ IMPLEMENTED
- `config.py`: `SECRET_KEY = "change_me_in_production"` — security issue
- Add validator: raise `ValueError` if secret is default in production environment
- Add `slowapi`: `@limiter.limit("10/minute")` on `POST /auth/login`
- Generate real secret: `python -c "import secrets; print(secrets.token_hex(32))"`

### 10. Rename llm_client.py + Historical AQI Chart [+1%, ~2 hrs] — ✅ IMPLEMENTED
- Rename `app/core/claude_client.py` → `app/core/llm_client.py`; update all imports
- `ReportsPage.tsx`: add Recharts `AreaChart` for 7-day hourly AQI trend
- Add AQI category color bands (green/yellow/orange/red) as chart background fills

---

## Score Progression

| After Phase | Score | Total Effort |
|-------------|-------|-------------|
| Current     | 61%   | —           |
| Phase 1     | 74%   | ~10 hrs     |
| Phase 2     | 87%   | ~26 hrs     |
| Phase 3     | 90%   | ~30 hrs     |

---

## What's Already Done (Do NOT Rebuild)

- Real-time AQI from WAQI + CPCB for 7 cities (30-min auto-refresh)
- Ward GeoJSON map with click-through to WardDetail
- 72h city forecast (diurnal-v1) + 72h ward hyperlocal forecast (ward-hyperlocal-v1)
- Chemical fingerprint + spatial dispersion source attribution
- NASA FIRMS fire hotspot detection
- OSM Overpass emission source discovery (all cities, no API key)
- Enforcement queue with ranked priority + Groq/LLaMA evidence briefs
- Multilingual advisories: EN, HI, KN, TA + IVR text (≤30 words)
- Multi-city comparison dashboard
- Reports: JSON + CSV export
- JWT auth + RBAC (sysadmin/admin/inspector/viewer roles)
- Public citizen portal
- AQI alerts auto-triggered at 200/300/400
