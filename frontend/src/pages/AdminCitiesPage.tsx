import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import {
  fetchCities,
  fetchWards,
  fetchStations,
  createCity,
  createWard,
  updateStation,
  deleteCity,
  deleteWard,
  deleteStation,
  initializeCityData,
  discoverEmissionSources,
  type CityWithCounts,
  type StationOut,
  type CreateCityPayload,
  type CreateWardPayload,
} from "@/features/cities/api";
import type { Ward } from "@/lib/types";


const TIMEZONES = [
  "Asia/Kolkata",
  "Asia/Colombo",
  "Asia/Karachi",
  "Asia/Dhaka",
  "Asia/Kathmandu",
  "UTC",
];

// Indian states and their major cities
const INDIA_STATES: Record<string, string[]> = {
  "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Tirupati", "Kurnool", "Nellore"],
  "Arunachal Pradesh": ["Itanagar", "Naharlagun", "Pasighat"],
  "Assam": ["Guwahati", "Silchar", "Dibrugarh", "Jorhat", "Nagaon"],
  "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga", "Purnia"],
  "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur", "Korba", "Durg"],
  "Goa": ["Panaji", "Vasco da Gama", "Margao", "Mapusa"],
  "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Gandhinagar"],
  "Haryana": ["Faridabad", "Gurugram", "Panipat", "Ambala", "Hisar", "Rohtak", "Karnal"],
  "Himachal Pradesh": ["Shimla", "Dharamsala", "Mandi", "Solan", "Kullu"],
  "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Deoghar"],
  "Karnataka": ["Bengaluru", "Mysuru", "Hubli", "Mangaluru", "Belagavi", "Kalaburagi", "Tumkur"],
  "Kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam", "Kannur"],
  "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar"],
  "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur", "Thane"],
  "Manipur": ["Imphal", "Thoubal", "Bishnupur"],
  "Meghalaya": ["Shillong", "Tura", "Jowai"],
  "Mizoram": ["Aizawl", "Lunglei", "Champhai"],
  "Nagaland": ["Kohima", "Dimapur", "Mokokchung"],
  "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Brahmapur", "Sambalpur", "Puri"],
  "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Mohali"],
  "Rajasthan": ["Jaipur", "Jodhpur", "Kota", "Ajmer", "Bikaner", "Udaipur", "Alwar"],
  "Sikkim": ["Gangtok", "Namchi", "Gyalshing"],
  "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli"],
  "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam"],
  "Tripura": ["Agartala", "Dharmanagar", "Udaipur"],
  "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra", "Varanasi", "Allahabad", "Meerut", "Ghaziabad", "Noida"],
  "Uttarakhand": ["Dehradun", "Haridwar", "Roorkee", "Haldwani", "Rishikesh"],
  "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri", "Bardhaman"],
  // Union Territories
  "Delhi": ["New Delhi", "Dwarka", "Rohini", "Pitampura", "Lajpat Nagar"],
  "Chandigarh": ["Chandigarh"],
  "Jammu & Kashmir": ["Srinagar", "Jammu", "Anantnag", "Baramulla"],
  "Ladakh": ["Leh", "Kargil"],
  "Puducherry": ["Puducherry", "Karaikal", "Mahe"],
  "Andaman & Nicobar Islands": ["Port Blair"],
  "Dadra & Nagar Haveli": ["Silvassa"],
  "Daman & Diu": ["Daman", "Diu"],
  "Lakshadweep": ["Kavaratti"],
};

// Known coordinates for major Indian cities — auto-filled when city is selected
const CITY_COORDS: Record<string, { lat: number; lon: number }> = {
  // Andhra Pradesh
  "Visakhapatnam": { lat: 17.6868, lon: 83.2185 },
  "Vijayawada":    { lat: 16.5062, lon: 80.6480 },
  "Guntur":        { lat: 16.3067, lon: 80.4365 },
  "Tirupati":      { lat: 13.6288, lon: 79.4192 },
  // Assam
  "Guwahati":      { lat: 26.1445, lon: 91.7362 },
  // Bihar
  "Patna":         { lat: 25.5941, lon: 85.1376 },
  // Chhattisgarh
  "Raipur":        { lat: 21.2514, lon: 81.6296 },
  // Goa
  "Panaji":        { lat: 15.4909, lon: 73.8278 },
  // Gujarat
  "Ahmedabad":     { lat: 23.0225, lon: 72.5714 },
  "Surat":         { lat: 21.1702, lon: 72.8311 },
  "Vadodara":      { lat: 22.3072, lon: 73.1812 },
  "Rajkot":        { lat: 22.3039, lon: 70.8022 },
  "Gandhinagar":   { lat: 23.2156, lon: 72.6369 },
  // Haryana
  "Faridabad":     { lat: 28.4089, lon: 77.3178 },
  "Gurugram":      { lat: 28.4595, lon: 77.0266 },
  "Panipat":       { lat: 29.3909, lon: 76.9635 },
  // Himachal Pradesh
  "Shimla":        { lat: 31.1048, lon: 77.1734 },
  // Jharkhand
  "Ranchi":        { lat: 23.3441, lon: 85.3096 },
  "Jamshedpur":    { lat: 22.8046, lon: 86.2029 },
  "Dhanbad":       { lat: 23.7957, lon: 86.4304 },
  // Karnataka
  "Bengaluru":     { lat: 12.9716, lon: 77.5946 },
  "Mysuru":        { lat: 12.2958, lon: 76.6394 },
  "Hubli":         { lat: 15.3647, lon: 75.1240 },
  "Mangaluru":     { lat: 12.9141, lon: 74.8560 },
  // Kerala
  "Thiruvananthapuram": { lat: 8.5241,  lon: 76.9366 },
  "Kochi":         { lat: 9.9312,  lon: 76.2673 },
  "Kozhikode":     { lat: 11.2588, lon: 75.7804 },
  // Madhya Pradesh
  "Bhopal":        { lat: 23.2599, lon: 77.4126 },
  "Indore":        { lat: 22.7196, lon: 75.8577 },
  "Jabalpur":      { lat: 23.1815, lon: 79.9864 },
  "Gwalior":       { lat: 26.2183, lon: 78.1828 },
  // Maharashtra
  "Mumbai":        { lat: 19.0760, lon: 72.8777 },
  "Pune":          { lat: 18.5204, lon: 73.8567 },
  "Nagpur":        { lat: 21.1458, lon: 79.0882 },
  "Nashik":        { lat: 19.9975, lon: 73.7898 },
  "Aurangabad":    { lat: 19.8762, lon: 75.3433 },
  "Thane":         { lat: 19.2183, lon: 72.9781 },
  // Odisha
  "Bhubaneswar":   { lat: 20.2961, lon: 85.8245 },
  "Cuttack":       { lat: 20.4625, lon: 85.8830 },
  "Rourkela":      { lat: 22.2604, lon: 84.8536 },
  // Punjab
  "Ludhiana":      { lat: 30.9010, lon: 75.8573 },
  "Amritsar":      { lat: 31.6340, lon: 74.8723 },
  "Jalandhar":     { lat: 31.3260, lon: 75.5762 },
  // Rajasthan
  "Jaipur":        { lat: 26.9124, lon: 75.7873 },
  "Jodhpur":       { lat: 26.2389, lon: 73.0243 },
  "Kota":          { lat: 25.2138, lon: 75.8648 },
  "Udaipur":       { lat: 24.5854, lon: 73.7125 },
  // Tamil Nadu
  "Chennai":       { lat: 13.0827, lon: 80.2707 },
  "Coimbatore":    { lat: 11.0168, lon: 76.9558 },
  "Madurai":       { lat: 9.9252,  lon: 78.1198 },
  "Tiruchirappalli": { lat: 10.7905, lon: 78.7047 },
  // Telangana
  "Hyderabad":     { lat: 17.3850, lon: 78.4867 },
  "Warangal":      { lat: 17.9784, lon: 79.5941 },
  // Uttar Pradesh
  "Lucknow":       { lat: 26.8467, lon: 80.9462 },
  "Kanpur":        { lat: 26.4499, lon: 80.3319 },
  "Agra":          { lat: 27.1767, lon: 78.0081 },
  "Varanasi":      { lat: 25.3176, lon: 82.9739 },
  "Allahabad":     { lat: 25.4358, lon: 81.8463 },
  "Meerut":        { lat: 28.9845, lon: 77.7064 },
  "Ghaziabad":     { lat: 28.6692, lon: 77.4538 },
  "Noida":         { lat: 28.5355, lon: 77.3910 },
  // Uttarakhand
  "Dehradun":      { lat: 30.3165, lon: 78.0322 },
  "Haridwar":      { lat: 29.9457, lon: 78.1642 },
  // West Bengal
  "Kolkata":       { lat: 22.5726, lon: 88.3639 },
  "Howrah":        { lat: 22.5958, lon: 88.2636 },
  "Durgapur":      { lat: 23.5204, lon: 87.3119 },
  "Siliguri":      { lat: 26.7271, lon: 88.3953 },
  // Union Territories
  "New Delhi":     { lat: 28.6139, lon: 77.2090 },
  "Chandigarh":    { lat: 30.7333, lon: 76.7794 },
  "Srinagar":      { lat: 34.0837, lon: 74.7973 },
  "Jammu":         { lat: 32.7266, lon: 74.8570 },
  "Leh":           { lat: 34.1526, lon: 77.5771 },
  "Puducherry":    { lat: 11.9416, lon: 79.8083 },
  "Port Blair":    { lat: 11.6234, lon: 92.7265 },
};

// ── Add City Form ─────────────────────────────────────────────────────────────

function AddCityForm({ onCreated }: { onCreated: (city: CityWithCounts) => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [state, setState] = useState("");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");

  const citiesForState = state ? (INDIA_STATES[state] ?? []) : [];

  function handleStateChange(newState: string) {
    setState(newState);
    setName("");
    setLat("");
    setLon("");
  }

  function handleCityChange(cityName: string) {
    setName(cityName);
    const coords = CITY_COORDS[cityName];
    if (coords) {
      setLat(String(coords.lat));
      setLon(String(coords.lon));
    } else {
      setLat("");
      setLon("");
    }
  }

  const mutation = useMutation({
    mutationFn: (p: CreateCityPayload) => createCity(p),
    onSuccess: (city) => {
      qc.invalidateQueries({ queryKey: ["admin-cities"] });
      onCreated(city);
      setName("");
      setState("");
      setTimezone("Asia/Kolkata");
      setLat("");
      setLon("");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const config_json: Record<string, unknown> = {};
    if (lat) config_json.lat = parseFloat(lat);
    if (lon) config_json.lon = parseFloat(lon);
    mutation.mutate({ name, state, timezone, config_json });
  }

  const coordsAutoFilled = !!(lat && lon && CITY_COORDS[name]);

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-400 mb-1">State / UT *</label>
          <select
            required
            value={state}
            onChange={(e) => handleStateChange(e.target.value)}
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-sky-500"
          >
            <option value="">— Select state —</option>
            {Object.keys(INDIA_STATES).sort().map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">City *</label>
          {citiesForState.length > 0 ? (
            <select
              required
              value={name}
              onChange={(e) => handleCityChange(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-sky-500"
            >
              <option value="">— Select city —</option>
              {citiesForState.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
              <option value="__custom__">Other (type below)</option>
            </select>
          ) : (
            <input
              required
              value={name}
              onChange={(e) => handleCityChange(e.target.value)}
              placeholder={state ? "Type city name" : "Select a state first"}
              disabled={!state}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 disabled:opacity-40"
            />
          )}
          {name === "__custom__" && (
            <input
              required
              autoFocus
              placeholder="Type city name"
              onChange={(e) => handleCityChange(e.target.value)}
              className="w-full mt-1.5 bg-slate-700 border border-sky-500 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none"
            />
          )}
        </div>
      </div>

      <div>
        <label className="block text-xs text-slate-400 mb-1">Timezone</label>
        <select
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-sky-500"
        >
          {TIMEZONES.map((tz) => (
            <option key={tz} value={tz}>{tz}</option>
          ))}
        </select>
      </div>

      {/* Lat / Lon — auto-filled from CITY_COORDS, editable for unknown cities */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-slate-400">Coordinates</label>
          {coordsAutoFilled && (
            <span className="text-xs text-emerald-400">✓ Auto-filled</span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <input
              type="number"
              step="any"
              required
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              placeholder="Latitude (e.g. 19.0760)"
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>
          <div>
            <input
              type="number"
              step="any"
              required
              value={lon}
              onChange={(e) => setLon(e.target.value)}
              placeholder="Longitude (e.g. 72.8777)"
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Used for weather fetching, fire hotspot detection, and map centering.
        </p>
      </div>

      {mutation.isError && (
        <p className="text-red-400 text-xs">{String((mutation.error as Error).message)}</p>
      )}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded transition-colors"
      >
        {mutation.isPending ? "Creating…" : "Create City"}
      </button>
    </form>
  );
}

// Pre-loaded ward data for major Indian cities (name + approximate population)
const WARDS_BY_CITY: Record<string, { name: string; population: number }[]> = {
  "New Delhi": [
    { name: "Connaught Place", population: 45000 },
    { name: "Dwarka", population: 520000 },
    { name: "Rohini", population: 680000 },
    { name: "Pitampura", population: 310000 },
    { name: "Lajpat Nagar", population: 180000 },
    { name: "Saket", population: 220000 },
    { name: "Janakpuri", population: 290000 },
    { name: "Karol Bagh", population: 270000 },
    { name: "Shahdara", population: 450000 },
    { name: "Anand Vihar", population: 160000 },
    { name: "Vasant Kunj", population: 200000 },
    { name: "Narela", population: 380000 },
  ],
  "Mumbai": [
    { name: "Andheri", population: 840000 },
    { name: "Bandra", population: 680000 },
    { name: "Borivali", population: 720000 },
    { name: "Dharavi", population: 550000 },
    { name: "Kurla", population: 510000 },
    { name: "Malad", population: 610000 },
    { name: "Mulund", population: 390000 },
    { name: "Santacruz", population: 430000 },
    { name: "Vikhroli", population: 340000 },
    { name: "Worli", population: 280000 },
    { name: "Colaba", population: 120000 },
    { name: "Ghatkopar", population: 580000 },
  ],
  "Bengaluru": [
    { name: "Whitefield", population: 520000 },
    { name: "Koramangala", population: 310000 },
    { name: "Indiranagar", population: 260000 },
    { name: "Hebbal", population: 340000 },
    { name: "Yelahanka", population: 480000 },
    { name: "Marathahalli", population: 430000 },
    { name: "BTM Layout", population: 350000 },
    { name: "Jayanagar", population: 290000 },
    { name: "Rajajinagar", population: 270000 },
    { name: "Malleshwaram", population: 220000 },
    { name: "Electronic City", population: 390000 },
    { name: "HSR Layout", population: 310000 },
  ],
  "Hyderabad": [
    { name: "Secunderabad", population: 450000 },
    { name: "Kukatpally", population: 540000 },
    { name: "Madhapur", population: 380000 },
    { name: "LB Nagar", population: 420000 },
    { name: "Uppal", population: 490000 },
    { name: "Ameerpet", population: 260000 },
    { name: "Begumpet", population: 210000 },
    { name: "Charminar", population: 310000 },
    { name: "Dilsukhnagar", population: 370000 },
    { name: "KPHB Colony", population: 320000 },
  ],
  "Chennai": [
    { name: "Anna Nagar", population: 340000 },
    { name: "Adyar", population: 290000 },
    { name: "Velachery", population: 410000 },
    { name: "Tambaram", population: 520000 },
    { name: "Porur", population: 380000 },
    { name: "Perambur", population: 360000 },
    { name: "Tondiarpet", population: 310000 },
    { name: "Mylapore", population: 250000 },
    { name: "T. Nagar", population: 280000 },
    { name: "Royapuram", population: 220000 },
    { name: "Sholinganallur", population: 430000 },
    { name: "Ambattur", population: 460000 },
  ],
  "Kolkata": [
    { name: "Dum Dum", population: 480000 },
    { name: "Behala", population: 560000 },
    { name: "Jadavpur", population: 390000 },
    { name: "Park Street", population: 180000 },
    { name: "Tollygunge", population: 340000 },
    { name: "Garden Reach", population: 310000 },
    { name: "Shyambazar", population: 270000 },
    { name: "Entally", population: 240000 },
    { name: "Watgunge", population: 200000 },
    { name: "New Market", population: 150000 },
  ],
  "Pune": [
    { name: "Shivajinagar", population: 320000 },
    { name: "Kothrud", population: 540000 },
    { name: "Hadapsar", population: 610000 },
    { name: "Pimpri", population: 480000 },
    { name: "Wakad", population: 390000 },
    { name: "Baner", population: 350000 },
    { name: "Kondhwa", population: 310000 },
    { name: "Yerawada", population: 270000 },
    { name: "Aundh", population: 290000 },
    { name: "Bibwewadi", population: 240000 },
  ],
  "Ahmedabad": [
    { name: "Naranpura", population: 410000 },
    { name: "Bopal", population: 380000 },
    { name: "Gota", population: 340000 },
    { name: "Chandkheda", population: 360000 },
    { name: "Vejalpur", population: 290000 },
    { name: "Vastrapur", population: 270000 },
    { name: "Maninagar", population: 320000 },
    { name: "Juhapura", population: 430000 },
    { name: "Nikol", population: 380000 },
    { name: "Naroda", population: 510000 },
  ],
  "Jaipur": [
    { name: "Vaishali Nagar", population: 380000 },
    { name: "Mansarovar", population: 450000 },
    { name: "Malviya Nagar", population: 310000 },
    { name: "Sanganer", population: 420000 },
    { name: "Pratap Nagar", population: 290000 },
    { name: "Sodala", population: 260000 },
    { name: "Murlipura", population: 240000 },
    { name: "Jagatpura", population: 350000 },
    { name: "Civil Lines", population: 180000 },
    { name: "Sindhi Camp", population: 150000 },
  ],
  "Lucknow": [
    { name: "Gomti Nagar", population: 520000 },
    { name: "Aliganj", population: 390000 },
    { name: "Indira Nagar", population: 460000 },
    { name: "Chowk", population: 310000 },
    { name: "Hazratganj", population: 220000 },
    { name: "Alambagh", population: 340000 },
    { name: "Chinhat", population: 280000 },
    { name: "Mahanagar", population: 370000 },
    { name: "Raja Bazar", population: 260000 },
    { name: "Aminabad", population: 240000 },
  ],
  "Visakhapatnam": [
    { name: "MVP Colony", population: 340000 },
    { name: "Gajuwaka", population: 480000 },
    { name: "Madhurawada", population: 390000 },
    { name: "Bheemunipatnam", population: 210000 },
    { name: "Seethammadhara", population: 270000 },
    { name: "Dwaraka Nagar", population: 230000 },
  ],
  "Surat": [
    { name: "Adajan", population: 510000 },
    { name: "Katargam", population: 480000 },
    { name: "Varachha", population: 620000 },
    { name: "Udhna", population: 430000 },
    { name: "Rander", population: 310000 },
    { name: "Athwa", population: 280000 },
  ],
};

// ── Add Ward Form ─────────────────────────────────────────────────────────────

function AddWardForm({ cityId, cityName, onCreated }: { cityId: string; cityName: string; onCreated: () => void }) {
  const qc = useQueryClient();
  const presetWards = WARDS_BY_CITY[cityName] ?? [];
  const [selectedPreset, setSelectedPreset] = useState("");
  const [name, setName] = useState("");
  const [population, setPopulation] = useState("");
  const [geojsonText, setGeojsonText] = useState("");
  const [geoError, setGeoError] = useState("");

  function handlePresetChange(val: string) {
    setSelectedPreset(val);
    if (val && val !== "__custom__") {
      const ward = presetWards.find((w) => w.name === val);
      if (ward) {
        setName(ward.name);
        setPopulation(String(ward.population));
      }
    } else if (val === "__custom__") {
      setName("");
      setPopulation("");
    }
  }

  const mutation = useMutation({
    mutationFn: (p: CreateWardPayload) => createWard(cityId, p),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-wards", cityId] });
      qc.invalidateQueries({ queryKey: ["admin-stations", cityId] });
      onCreated();
      setSelectedPreset("");
      setName("");
      setPopulation("");
      setGeojsonText("");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setGeoError("");
    let geometry: Record<string, unknown> | null = null;
    if (geojsonText.trim()) {
      try {
        geometry = JSON.parse(geojsonText);
      } catch {
        setGeoError("Invalid GeoJSON");
        return;
      }
    }
    mutation.mutate({
      name,
      population: population ? parseInt(population, 10) : null,
      geometry,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 mt-3">
      {presetWards.length > 0 && (
        <div>
          <label className="block text-xs text-slate-400 mb-1">Select ward *</label>
          <select
            value={selectedPreset}
            onChange={(e) => handlePresetChange(e.target.value)}
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
          >
            <option value="">— Choose a ward —</option>
            {presetWards.map((w) => (
              <option key={w.name} value={w.name}>{w.name}</option>
            ))}
            <option value="__custom__">Other (type manually)</option>
          </select>
        </div>
      )}
      {(presetWards.length === 0 || selectedPreset === "__custom__") && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Ward name *</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Bandra"
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Population</label>
            <input
              type="number"
              min={0}
              value={population}
              onChange={(e) => setPopulation(e.target.value)}
              placeholder="e.g. 500000"
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>
      )}
      {selectedPreset && selectedPreset !== "__custom__" && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Ward name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Population</label>
            <input
              type="number"
              min={0}
              value={population}
              onChange={(e) => setPopulation(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>
      )}
      <div>
        <label className="block text-xs text-slate-400 mb-1">
          Geometry — paste GeoJSON MultiPolygon (optional)
        </label>
        <textarea
          value={geojsonText}
          onChange={(e) => setGeojsonText(e.target.value)}
          placeholder='{"type":"MultiPolygon","coordinates":[[[[77.2,28.6],[77.3,28.6],[77.3,28.7],[77.2,28.7],[77.2,28.6]]]]}'
          rows={4}
          className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 font-mono focus:outline-none focus:border-emerald-500 resize-none"
        />
        {geoError && <p className="text-red-400 text-xs mt-1">{geoError}</p>}
      </div>
      {mutation.isError && (
        <p className="text-red-400 text-xs">{String((mutation.error as Error).message)}</p>
      )}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded transition-colors"
      >
        {mutation.isPending ? "Adding…" : "Add Ward"}
      </button>
    </form>
  );
}

// ── Ward Delete Button (used in nested layout) ────────────────────────────────

function WardDeleteButton({ ward, cityId, onDeleted }: { ward: Ward; cityId: string; onDeleted: () => void }) {
  const [confirm, setConfirm] = useState(false);
  const mutation = useMutation({ mutationFn: () => deleteWard(cityId, ward.id), onSuccess: onDeleted });

  if (confirm) {
    return (
      <span className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
        <span className="text-xs text-red-400">Delete ward?</span>
        <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
          className="px-1.5 py-0.5 rounded bg-red-600 hover:bg-red-500 text-white text-xs font-semibold disabled:opacity-50 transition-colors">
          {mutation.isPending ? "…" : "Yes"}
        </button>
        <button onClick={() => setConfirm(false)}
          className="px-1.5 py-0.5 rounded bg-slate-600 hover:bg-slate-500 text-white text-xs transition-colors">
          No
        </button>
      </span>
    );
  }
  return (
    <button onClick={(e) => { e.stopPropagation(); setConfirm(true); }}
      className="text-xs text-red-400 hover:text-red-300 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
      Delete
    </button>
  );
}

// ── Station Row (inline edit) ─────────────────────────────────────────────────

function StationRow({
  station,
  cityId,
  wards,
  onUpdated,
}: {
  station: StationOut;
  cityId: string;
  wards: Ward[];
  onUpdated: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(station.name);
  const [wardId, setWardId] = useState(station.ward_id ?? "");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      updateStation(cityId, station.id, {
        name,
        ward_id: wardId || null,
        is_active: station.is_active,
      }),
    onSuccess: () => {
      setEditing(false);
      onUpdated();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteStation(cityId, station.id),
    onSuccess: onUpdated,
  });

  const geo = station.geometry as Record<string, unknown> | null;
  const coords = geo?.coordinates as number[] | null;
  const assignedWard = wards.find((w) => w.id === (wardId || station.ward_id));

  if (editing) {
    return (
      <tr className="border-b border-slate-700/50 bg-slate-700/30">
        <td className="py-2 pr-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-slate-600 border border-slate-500 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-violet-400"
          />
        </td>
        <td className="py-2 pr-2 text-slate-400 font-mono text-xs">
          {station.external_station_code}
        </td>
        <td className="py-2 pr-2">
          <select
            value={wardId}
            onChange={(e) => setWardId(e.target.value)}
            className="w-full bg-slate-600 border border-slate-500 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-violet-400"
          >
            <option value="">— None —</option>
            {wards.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
        </td>
        <td className="py-2 pr-2">
          <span className={`text-xs font-semibold ${station.is_active ? "text-green-400" : "text-slate-500"}`}>
            {station.is_active ? "Active" : "Inactive"}
          </span>
        </td>
        <td className="py-2">
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="px-2 py-0.5 rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors"
            >
              {mutation.isPending ? "…" : "Save"}
            </button>
            <button
              onClick={() => { setEditing(false); setName(station.name); setWardId(station.ward_id ?? ""); }}
              className="px-2 py-0.5 rounded bg-slate-600 hover:bg-slate-500 text-white text-xs transition-colors"
            >
              Cancel
            </button>
          </div>
          {mutation.isError && <p className="text-red-400 text-xs mt-0.5">Failed</p>}
        </td>
      </tr>
    );
  }

  return (
    <tr className="border-b border-slate-700/50 last:border-0 group">
      <td className="py-1.5 text-white">{station.name}</td>
      <td className="py-1.5 text-slate-400 font-mono text-xs">{station.external_station_code}</td>
      <td className="py-1.5 text-slate-400 text-xs">
        {assignedWard ? assignedWard.name : coords ? `${coords[1].toFixed(4)}, ${coords[0].toFixed(4)}` : "—"}
      </td>
      <td className="py-1.5">
        <span className={`text-xs font-semibold ${station.is_active ? "text-green-400" : "text-slate-500"}`}>
          {station.is_active ? "Active" : "Inactive"}
        </span>
      </td>
      <td className="py-1.5">
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-violet-400 hover:text-violet-300 font-medium"
          >
            Edit
          </button>
          {confirmDelete ? (
            <span className="flex items-center gap-1">
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="px-1.5 py-0.5 rounded bg-red-600 hover:bg-red-500 text-white text-xs font-semibold disabled:opacity-50 transition-colors"
              >
                {deleteMutation.isPending ? "…" : "Yes"}
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-1.5 py-0.5 rounded bg-slate-600 hover:bg-slate-500 text-white text-xs transition-colors"
              >
                No
              </button>
            </span>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="text-xs text-red-400 hover:text-red-300"
            >
              Delete
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

// ── City Row (expanded detail) ────────────────────────────────────────────────

function CityRow({ city }: { city: CityWithCounts }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [addingWard, setAddingWard] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  // which ward accordion is currently expanded
  const [openWardId, setOpenWardId] = useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: () => deleteCity(city.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-cities"] });
    },
  });

  const [initDone, setInitDone] = useState<string | null>(null);
  const initMutation = useMutation({
    mutationFn: () => initializeCityData(city.id),
    onSuccess: (result) => {
      setInitDone(`✓ ${result.readings} live readings fetched · forecast & enforcement updated`);
      setTimeout(() => setInitDone(null), 6000);
    },
  });

  const [discoverMsg, setDiscoverMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const discoverMutation = useMutation({
    mutationFn: () => discoverEmissionSources(city.id),
    onSuccess: (result) => {
      if (result.error) {
        setDiscoverMsg({ text: `⚠ ${result.error}`, ok: false });
      } else if (result.discovered === 0) {
        setDiscoverMsg({ text: "No emission sources found near this city in OSM — try adding manually.", ok: false });
      } else {
        setDiscoverMsg({
          text: `✓ Found ${result.discovered} sources · ${result.imported} imported · ${result.skipped} already existed`,
          ok: true,
        });
      }
      setTimeout(() => setDiscoverMsg(null), 10000);
    },
  });

  const wardsQ = useQuery({
    queryKey: ["admin-wards", city.id],
    queryFn: () => fetchWards(city.id),
  });

  const stationsQ = useQuery<StationOut[]>({
    queryKey: ["admin-stations", city.id],
    queryFn: () => fetchStations(city.id),
  });

  const wardCount = wardsQ.data?.length ?? "—";
  const stationCount = stationsQ.data?.length ?? "—";

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 overflow-hidden">
      {/* Header row */}
      <div className="flex items-center gap-4 px-4 py-3 hover:bg-slate-700/40 transition-colors">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-4 flex-1 min-w-0 text-left"
        >
          <span className="text-lg shrink-0">{open ? "▾" : "▸"}</span>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-white truncate">{city.name}</p>
            <p className="text-xs text-slate-400">
              {city.state} · {city.timezone}
            </p>
          </div>
        </button>
        <div className="flex items-center gap-4 text-xs text-slate-400 shrink-0">
          <span>
            <span className="text-white font-semibold">{wardCount}</span> wards
          </span>
          <span>
            <span className="text-white font-semibold">{stationCount}</span> stations
          </span>
          <span className="px-2 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 text-xs font-semibold uppercase">
            active
          </span>
          {confirmDelete ? (
            <span className="flex items-center gap-1">
              <span className="text-red-400">Delete?</span>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="px-2 py-0.5 rounded bg-red-600 hover:bg-red-500 text-white text-xs font-semibold disabled:opacity-50 transition-colors"
              >
                {deleteMutation.isPending ? "…" : "Yes"}
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-2 py-0.5 rounded bg-slate-600 hover:bg-slate-500 text-white text-xs font-semibold transition-colors"
              >
                No
              </button>
            </span>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="px-2 py-0.5 rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs font-semibold transition-colors"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {/* Expanded detail */}
      {open && (
        <div className="border-t border-slate-800 px-4 py-4 space-y-5">
          {/* Initialize data banner */}
          {(() => {
            const hasStations = (stationsQ.data?.length ?? 0) > 0;
            return (
              <div className={`flex items-center gap-3 p-3 rounded-lg border ${hasStations ? "bg-slate-700/40 border-slate-600" : "bg-amber-500/5 border-amber-500/30"}`}>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-slate-200">Initialize city data</p>
                  {!hasStations ? (
                    <p className="text-xs text-amber-400 mt-0.5">
                      No stations yet — add at least one station above before initializing.
                    </p>
                  ) : (
                    <p className="text-xs text-slate-400 mt-0.5">
                      Pulls readings from {stationsQ.data!.length} station{stationsQ.data!.length !== 1 ? "s" : ""}, fetches weather, and generates the 72-hour forecast.
                    </p>
                  )}
                  {initDone && <p className="text-xs text-emerald-400 mt-1">{initDone}</p>}
                  {initMutation.isError && (
                    <p className="text-xs text-red-400 mt-1">Failed — check backend logs</p>
                  )}
                </div>
                <button
                  onClick={() => initMutation.mutate()}
                  disabled={initMutation.isPending || !hasStations}
                  className="shrink-0 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold transition-colors"
                >
                  {initMutation.isPending ? "Initializing…" : "Initialize"}
                </button>
              </div>
            );
          })()}

          {/* Discover emission sources banner */}
          <div className="flex items-center gap-3 p-3 rounded-lg border bg-slate-700/40 border-slate-600">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-slate-200">
                Emission Sources
                <span className="ml-2 text-slate-400 font-normal">— auto-discovered from OpenStreetMap</span>
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                Finds industrial zones, bus depots, construction sites, and power plants within 15 km of the city centre. New sources are ranked automatically in the enforcement queue.
              </p>
              {discoverMsg && (
                <p className={`text-xs mt-1 ${discoverMsg.ok ? "text-emerald-400" : "text-amber-400"}`}>
                  {discoverMsg.text}
                </p>
              )}
              {discoverMutation.isError && (
                <p className="text-xs text-red-400 mt-1">Discovery failed — check backend logs</p>
              )}
            </div>
            <button
              onClick={() => discoverMutation.mutate()}
              disabled={discoverMutation.isPending}
              className="shrink-0 px-3 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold transition-colors"
            >
              {discoverMutation.isPending ? "Discovering…" : "Discover Sources"}
            </button>
          </div>

          {/* Wards + Stations nested section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-slate-200">Wards &amp; Stations</h4>
              <button
                onClick={() => setAddingWard((v) => !v)}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-medium"
              >
                {addingWard ? "Cancel" : "+ Add Ward"}
              </button>
            </div>

            {wardsQ.isLoading && <p className="text-xs text-slate-500">Loading…</p>}
            {wardsQ.data && wardsQ.data.length === 0 && (
              <p className="text-xs text-slate-500 italic">No wards yet — add a ward first, then add stations inside it.</p>
            )}

            {/* Each ward expands to show its own stations */}
            <div className="space-y-2">
              {(wardsQ.data ?? []).map((w) => {
                const wardStations = (stationsQ.data ?? []).filter((s) => s.ward_id === w.id);
                const isOpen = openWardId === w.id;
                return (
                  <div key={w.id} className="rounded-lg border border-slate-600 overflow-hidden">
                    {/* Ward header */}
                    <div className={`flex items-center gap-3 px-3 py-2 transition-colors ${isOpen ? "bg-emerald-500/10" : "bg-slate-700/50 hover:bg-slate-700"}`}>
                      <button
                        onClick={() => setOpenWardId(isOpen ? null : w.id)}
                        className="flex items-center gap-2 flex-1 min-w-0 text-left"
                      >
                        <span className="text-slate-400 text-sm">{isOpen ? "▾" : "▸"}</span>
                        <span className={`font-medium text-sm ${isOpen ? "text-emerald-300" : "text-white"}`}>{w.name}</span>
                        <span className="text-xs text-slate-500 ml-1">
                          {w.population ? `· ${w.population.toLocaleString()} people` : ""}
                        </span>
                        <span className={`ml-auto text-xs ${wardStations.length > 0 ? "text-slate-400" : "text-slate-600"}`}>
                          {wardStations.length} station{wardStations.length !== 1 ? "s" : ""}
                        </span>
                        {!(w as unknown as Record<string, unknown>).geometry && (
                          <span className="text-xs text-amber-500 ml-2" title="No boundary geometry">No geometry</span>
                        )}
                      </button>
                      <WardDeleteButton ward={w} cityId={city.id} onDeleted={() => { wardsQ.refetch(); stationsQ.refetch(); if (isOpen) setOpenWardId(null); }} />
                    </div>

                    {/* Ward expanded: auto-assigned station info */}
                    {isOpen && (
                      <div className="border-t border-slate-600 bg-slate-800/60 px-3 py-2.5">
                        <p className="text-xs text-slate-500 mb-2 uppercase tracking-wide font-medium">CAAQMS Station</p>
                        {wardStations.length === 0 ? (
                          <p className="text-xs text-amber-400">
                            No station assigned yet — station is auto-assigned when the ward is saved with a boundary.
                          </p>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {wardStations.map((s) => (
                              <div key={s.id} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-700 border border-slate-600">
                                <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
                                <span className="text-sm text-white font-medium">{s.name}</span>
                                <span className="text-xs text-slate-400 font-mono">{s.external_station_code}</span>
                                <span className={`text-xs ${s.is_active ? "text-emerald-400" : "text-slate-500"}`}>
                                  {s.is_active ? "Active" : "Inactive"}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Unassigned stations */}
            {(() => {
              const unassigned = (stationsQ.data ?? []).filter((s) => !s.ward_id);
              if (unassigned.length === 0) return null;
              return (
                <div className="mt-2 rounded-lg border border-slate-600 border-dashed overflow-hidden">
                  <div className="flex items-center gap-2 px-3 py-2 bg-slate-700/30">
                    <span className="text-xs text-amber-400 font-medium">⚠ Unassigned stations ({unassigned.length})</span>
                    <span className="text-xs text-slate-500">— use Edit to assign a ward</span>
                  </div>
                  <div className="px-3 py-2">
                    <table className="w-full text-sm">
                      <tbody>
                        {unassigned.map((s) => (
                          <StationRow
                            key={s.id}
                            station={s}
                            cityId={city.id}
                            wards={wardsQ.data ?? []}
                            onUpdated={() => stationsQ.refetch()}
                          />
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })()}

            {addingWard && (
              <div className="mt-3">
                <AddWardForm
                  cityId={city.id}
                  cityName={city.name}
                  onCreated={() => { setAddingWard(false); wardsQ.refetch(); }}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdminCitiesPage() {
  useAuth();
  const [showAddCity, setShowAddCity] = useState(false);

  const citiesQ = useQuery({
    queryKey: ["admin-cities"],
    queryFn: fetchCities,
  });

  function handleCityCreated(city: CityWithCounts) {
    setShowAddCity(false);
    // queryClient is invalidated inside AddCityForm
    console.log("Created city:", city.id);
  }

  return (
    <div className="flex-1 overflow-auto bg-slate-950 text-white">
      <main>
        <div className="px-8 py-6 max-w-4xl">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-white">City Onboarding</h1>
              <p className="text-slate-400 text-sm mt-1">
                Manage cities, wards, and monitoring stations
              </p>
            </div>
            <button
              onClick={() => setShowAddCity((v) => !v)}
              className="bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {showAddCity ? "Cancel" : "+ Add City"}
            </button>
          </div>

          {/* Add City Form */}
          {showAddCity && (
            <div className="mb-6 bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="text-base font-semibold text-white mb-4">New City</h3>
              <AddCityForm onCreated={handleCityCreated} />
            </div>
          )}

          {/* City list */}
          {citiesQ.isLoading && (
            <div className="text-slate-400 text-sm py-8 text-center">Loading cities…</div>
          )}
          {citiesQ.isError && (
            <div className="text-red-400 text-sm py-4">Failed to load cities.</div>
          )}
          {citiesQ.data && citiesQ.data.length === 0 && (
            <div className="text-slate-500 text-sm py-8 text-center italic">
              No cities yet. Click "+ Add City" to onboard the first city.
            </div>
          )}
          <div className="space-y-3">
            {citiesQ.data?.map((city) => (
              <CityRow key={city.id} city={city} />
            ))}
          </div>
        </div>
      </main>
  </div>
  );
}
