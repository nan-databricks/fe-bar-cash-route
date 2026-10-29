// Synthetic Siam Northeast Bank (fictional) branches around Khon Kaen.
// Offline fallback only — the backend (/api/branch-inputs) supplies the full 159-branch estate.

export interface RawBranch {
  code: string;
  name: string;
  district: string;
  lat: number;
  lng: number;
  isDepot?: boolean;
}

export const RAW_BRANCHES: RawBranch[] = [
  {
    code: "DEP-KKN-C",
    name: "SNB Khon Kaen Central Cash Centre",
    district: "Mueang Khon Kaen",
    lat: 16.441,
    lng: 102.835,
    isDepot: true,
  },
  { code: "SNB-B001", name: "SNB Mueang Khon Kaen Service Branch 001", district: "Mueang Khon Kaen", lat: 16.4322, lng: 102.8236 },
  { code: "SNB-B008", name: "SNB Mueang Khon Kaen Service Branch 008", district: "Mueang Khon Kaen", lat: 16.4515, lng: 102.814 },
  { code: "SNB-B015", name: "SNB Mueang Khon Kaen Service Branch 015", district: "Mueang Khon Kaen", lat: 16.4749, lng: 102.8226 },
  { code: "SNB-B022", name: "SNB Mueang Khon Kaen Service Branch 022", district: "Mueang Khon Kaen", lat: 16.4198, lng: 102.8489 },
  { code: "SNB-B029", name: "SNB Mueang Khon Kaen Service Branch 029", district: "Mueang Khon Kaen", lat: 16.4291, lng: 102.8305 },
  { code: "SNB-B007", name: "SNB Ban Phai Service Branch 007", district: "Ban Phai", lat: 16.06, lng: 102.735 },
  { code: "SNB-B004", name: "SNB Chum Phae Service Branch 004", district: "Chum Phae", lat: 16.543, lng: 102.31 },
  { code: "SNB-B002", name: "SNB Nam Phong Service Branch 002", district: "Nam Phong", lat: 16.705, lng: 102.862 },
  { code: "SNB-B011", name: "SNB Chum Phae Service Branch 011", district: "Chum Phae", lat: 16.499, lng: 102.442 },
  { code: "SNB-B005", name: "SNB Mancha Khiri Service Branch 005", district: "Mancha Khiri", lat: 16.2, lng: 102.533 },
  { code: "SNB-B009", name: "SNB Nam Phong Service Branch 009", district: "Nam Phong", lat: 16.71, lng: 103.0 },
  { code: "SNB-B006", name: "SNB Phon Service Branch 006", district: "Phon", lat: 15.82, lng: 102.6 },
  { code: "SNB-B016", name: "SNB Nam Phong Service Branch 016", district: "Nam Phong", lat: 16.77, lng: 102.62 },
  { code: "SNB-B003", name: "SNB Ban Haet Service Branch 003", district: "Ban Haet", lat: 16.195, lng: 102.77 },
];
