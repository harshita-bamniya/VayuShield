Project root: E:\GalaxyWeblinks\Hackathon\vayushield-ai

Before writing any code, read these files in order:
1. backend/app/api/v1/ingestion.py
2. backend/app/modules/ingestion/repository.py
3. frontend/src/features/cities/api.ts
4. frontend/src/pages/Dashboard.tsx

---

# Task: Add Fire Hotspot Markers to the Dashboard Map

## Project stack
- Backend: FastAPI + SQLAlchemy async + PostgreSQL/TimescaleDB
- Frontend: React 18, TypeScript, Vite, TailwindCSS, React Query, Leaflet map
- Admin login: admin@vayushield.local / Admin@123
- Delhi city ID (seeded in DB): a1b2c3d4-e5f6-7890-abcd-ef1234567890

## What is already done — do NOT touch these

- NASA FIRMS fire hotspot data is already being fetched from the real API and stored in the `fire_hotspots` DB table by the background job in `backend/app/jobs/ingestion_jobs.py`
- The fire connector lives at `backend/app/modules/ingestion/connectors/fire_hotspots.py`
- The `fire_hotspots` table has these columns: `id, city_id, detected_at, geometry (PostGIS Point), confidence (float 0–100), frp (float, Fire Radiative Power in MW), source (str)`
- `insert_fire_hotspot()` already exists in `backend/app/modules/ingestion/repository.py`
- The dashboard map already exists in `frontend/src/pages/Dashboard.tsx` and uses Leaflet
- All API endpoints follow the pattern `/api/v1/cities/{city_id}/...` and require JWT Bearer auth

## What you need to build

### Step 1 — Backend endpoint
Add this endpoint to `backend/app/api/v1/ingestion.py` following the same pattern as existing endpoints in that file:

```
GET /api/v1/cities/{city_id}/fire-hotspots?hours_back=24
```

- Requires JWT auth (same dependency as other endpoints in that file)
- Query `fire_hotspots` where `city_id = :city_id AND detected_at > NOW() - INTERVAL '24 hours'`
- Extract lat/lon from PostGIS geometry using `ST_Y(geometry::geometry)` and `ST_X(geometry::geometry)`
- Return list of: `{ id, detected_at, lat, lon, confidence, frp, source }`

### Step 2 — Frontend API function
Add to `frontend/src/features/cities/api.ts`:

```typescript
export interface FireHotspot {
  id: string;
  detected_at: string;
  lat: number;
  lon: number;
  confidence: number;
  frp: number | null;
  source: string;
}

export async function fetchFireHotspots(cityId: string, hoursBack = 24): Promise<FireHotspot[]>
```

Follow the exact same auth header pattern used by other fetch functions already in that file.

### Step 3 — Map markers in Dashboard.tsx
- Add a React Query call using `fetchFireHotspots` with 5-minute refetch interval
- Add Leaflet circle markers for each hotspot:
  - Color: `confidence >= 75` → red `#ef4444`, else orange `#f97316`
  - Radius: `frp ? Math.max(6, Math.min(20, frp / 10)) : 8`
- On marker click show a popup:
  ```
  Fire Detected
  Time: <detected_at formatted>
  Confidence: <value>% (High/Normal)
  FRP: <value> MW
  Source: NASA FIRMS
  ```
- Add two entries to the existing map legend: fire high confidence (red) and fire normal (orange)

## Done when
- [ ] Fire markers appear on the Delhi map for any hotspots in the DB
- [ ] Clicking a marker shows the popup with confidence, FRP, time
- [ ] No crash when the table is empty (July is low-fire season, table may be empty — seed one test row in the DB to verify rendering)
- [ ] Markers auto-refresh every 5 minutes
- [ ] `npx tsc --noEmit` passes with no errors
- [ ] All 79 backend tests still pass (`pytest` run from `backend/`)
