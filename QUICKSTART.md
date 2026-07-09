# VayuShield AI — Quick Start

## Run

```bash
docker-compose up --build
```

## Open

```
http://localhost:5173
```

## Login

```
Email:    admin@vayushield.local
Password: Admin@123
```

## Pages

| Page | URL | What to do |
|---|---|---|
| Dashboard | `/dashboard` | View live City AQI, 72h forecast chart, ward map — click a ward polygon to drill in |
| Enforcement | `/enforcement` | See ranked pollution sources — click ▼ to expand evidence brief, hit **Dispatch** to assign an inspector |
| Advisories | `/advisories` | Browse all 12 advisories by AQI level — filter by language, click **Generate Advisories** to create new ones |
| Reports | `/reports` | View AQI stats, ward table, enforcement priorities — change period (7/30/90 days), click **Download CSV** |
| City Admin | `/admin/cities` | Add new cities, wards (paste GeoJSON), and monitoring stations |

## Stop

```bash
docker-compose down
```
