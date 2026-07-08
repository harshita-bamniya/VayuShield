import { create } from "zustand";
import type { City } from "@/lib/types";

interface CitiesState {
  selectedCityId: string | null;
  selectedCity: City | null;
  setSelectedCity: (city: City) => void;
  clearSelectedCity: () => void;
}

export const useCities = create<CitiesState>((set) => ({
  selectedCityId: null,
  selectedCity: null,

  setSelectedCity: (city) =>
    set({ selectedCityId: city.id, selectedCity: city }),

  clearSelectedCity: () =>
    set({ selectedCityId: null, selectedCity: null }),
}));
