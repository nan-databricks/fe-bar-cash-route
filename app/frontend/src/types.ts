export type CashStatus = "REPLENISH" | "PICKUP" | "OK";

export interface Branch {
  id: string;
  code: string;
  name: string;
  district: string;
  lat: number;
  lng: number;
  isDepot?: boolean;
  // ML model outputs (predicted for the planning day, THB)
  predictedInflow: number;
  predictedOutflow: number;
  // Operational cash state (THB)
  openingCash: number;
  cashCapacity: number;
  minThreshold: number;
  // Derived
  netFlow: number; // inflow - outflow
  projectedClosingCash: number;
  status: CashStatus;
  demand: number; // signed THB: positive = deliver (replenish), negative = pickup excess
  serviceMinutes: number;
  windowStart: string; // "HH:MM"
  windowEnd: string;
}

export interface RouteStop {
  branchId: string;
  seq: number;
  arrival: string; // "HH:MM"
  legDistanceKm: number;
  cumulativeKm: number;
}

export interface VehicleRoute {
  vehicleId: string;
  label: string;
  color: string;
  stops: RouteStop[];
  path: [number, number][]; // ordered coords incl depot at both ends
  totalDistanceKm: number;
  driveMinutes: number;
  serviceMinutes: number;
  cashDelivered: number;
  cashPickedUp: number;
}

export interface RoutePlan {
  kind: "OPTIMIZED" | "ORIGINAL";
  vehicles: VehicleRoute[];
  totalDistanceKm: number;
  totalDriveMinutes: number;
  totalServiceMinutes: number;
  totalManHours: number;
  vehiclesUsed: number;
  branchesServed: number;
}

export interface ExecMetrics {
  distanceSavedKm: number;
  distanceSavedPct: number;
  manHoursSaved: number;
  manHoursSavedPct: number;
  vehiclesSaved: number;
  fuelCostSavedThb: number;
  idleCashBeforeThb: number;
  idleCashAfterThb: number;
  idleCashReductionThb: number;
  idleCashReductionPct: number;
  co2SavedKg: number;
  onTimePct: number;
  branchesServed: number;
  branchesTotal: number;
}

export interface PlanBundle {
  planDate: string;
  region: string;
  branches: Branch[];
  optimized: RoutePlan;
  original: RoutePlan;
  metrics: ExecMetrics;
}

// ---- Dynamic input model ----
// The raw, user-editable inputs. Everything else (status, demand, routes,
// metrics) is DERIVED from these by the plan builder.
export interface BranchInput {
  code: string;
  name: string;
  district: string;
  lat: number;
  lng: number;
  isDepot?: boolean;
  cashCapacity: number; // vault capacity (THB)
  minThreshold: number; // minimum operating cash (THB)
  openingCash: number; // start-of-day balance (THB)
  predictedInflow: number; // ML model output (THB)
  predictedOutflow: number; // ML model output (THB)
  serviceMinutes?: number; // dwell time; auto if omitted
  windowStart?: string; // "HH:MM"
  windowEnd?: string; // "HH:MM"
}

export interface OptimizerParams {
  planDate: string;
  region: string;
  numVans: number;
  vanCashCapacity: number; // THB per van (reference)
  roadFactor: number; // straight-line -> road multiplier
  avgSpeedKmh: number;
  costPerKmThb: number;
  co2PerKmKg: number;
  crewPerVehicle: number;
  replenishTargetPct: number; // refill target as % of capacity (e.g. 0.6)
  excessLinePct: number; // pickup trigger as % of capacity (e.g. 0.8)
  keepPct: number; // cash to leave after pickup, % of capacity (e.g. 0.5)
  cityServiceMin: number;
  districtServiceMin: number;
  idleCashResidualPct: number; // % of idle cash still idle after optimization
}

export interface AppConfig {
  params: OptimizerParams;
  branches: BranchInput[];
}

// ---- Machine & Branch tracking ----
export type Health = "Healthy" | "Watch" | "Action Needed" | "Critical" | "No Data";
export type TrackAction = "Deliver" | "Pickup" | "Both" | "No Action";
export type RiskLevel = "Very High" | "High" | "Medium" | "Low";

export interface DayFlow {
  day: string; // "DD MMM"
  deposit: number;
  withdraw: number;
  net: number;
}

export interface Denomination {
  b1000: number;
  b500: number;
  b100: number;
  b50: number;
}

// Editable machine input (everything else is derived from these).
export interface MachineInput {
  id: string;
  location: string;
  district: string;
  lat: number;
  lng: number;
  currentCash: number; // THB currently in the machine
  predictedEod: number; // ML predicted end-of-day cash, THB
  cashCapacity: number; // cassette capacity, THB
  confidence: number; // ML confidence %
}

export interface Machine extends MachineInput {
  nodeType?: string;
  depotId?: string;
  action: TrackAction;
  health: Health;
  riskLevel: RiskLevel;
  emergency: boolean;
  depositToday: number;
  withdrawToday: number;
  denomination: Denomination;
  trend: DayFlow[];
}

export interface BranchTrack {
  code: string;
  name: string;
  district: string;
  lat: number;
  lng: number;
  currentCash: number;
  deposit: number; // predicted daily deposit inflow
  withdraw: number; // predicted daily withdrawal outflow
  forecastNet: number; // net position vs threshold (signed)
  action: TrackAction;
  health: Health;
  confidence: number;
  emergency: boolean;
  trend: DayFlow[];
  denominationGap: Denomination; // signed note-level surplus/shortfall
}

// ---- Route execution / tracking (the customer's OR-Tools output format) ----
export type RouteStatus = "On Track" | "Delayed" | "At Risk";
export type StopType = "Start" | "Deliver" | "Pickup" | "Mixed" | "Return";
export type StopStatus = "Completed" | "In Progress" | "Pending";

export interface RouteStopExec {
  seq: number;
  code: string; // branch / cash-point code ("DEPOT" for start & return)
  location: string;
  type: StopType;
  status: StopStatus;
  eta: string; // "HH:MM"
  lat: number;
  lng: number;
  amount: number; // signed THB: +deliver, -pickup, 0 depot
  nodeType?: string; // BRANCH | ATM | RCM
}

export interface RouteExecution {
  routeId: string; // "OPT-C-01"
  truckId: string; // "VAN-01"
  planType?: "OPTIMIZED" | "BASELINE";
  depotId?: string;
  citCostThb?: number;
  durationMin?: number;
  label: string; // human label / zone
  status: RouteStatus;
  depot: string; // start/return depot name
  depotLat: number;
  depotLng: number;
  totalStops: number; // service stops (excl. start & return)
  completed: number;
  remaining: number;
  distanceKm: number;
  distanceLeftKm: number;
  etaReturn: string; // "HH:MM"
  vehicleCapacity: number; // THB cash capacity of the van
  cashOnBoard: number; // THB currently secured on the truck (net)
  pickupAmount: number; // THB collected
  deliveryAmount: number; // THB dispensed
  color: string;
  path: [number, number][]; // depot -> stops -> depot
  stops: RouteStopExec[]; // includes Start and Return rows
}
