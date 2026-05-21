import React, { createContext, useContext, useState, ReactNode, useMemo } from 'react';

export type AnalyticalLens = 'case' | 'commodity' | 'corridor' | 'incident-replay';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface RiskCorridor {
  corridor_id: string;
  hts_chapter: string;
  hts_6digit: string;
  industry_segment: string;
  origin_country: string;
  destination_country: string;
  supplier_entity: string;
  shipment_count: number;
  aggregate_value_usd: number;
  yoy_volume_surge_pct: number;
  yoy_value_surge_pct: number;
  macro_volumetric_delta: {
    status: 'FLAGGED' | 'NORMAL';
    outbound_volume_manifest_tons: number;
    estimated_period_capacity_tons: number;
    ratio: number;
    signal: string;
  };
  ad_cvd_rate_pct: number;
  active_vessels: number;
  risk_level: RiskLevel;
  last_updated: string;
  manifest_ids?: string[];
}

export interface Vessel {
  vessel_id: string;
  vessel_name: string;
  flag_state: string;
  current_port: string;
  status: 'AT_BERTH' | 'INBOUND' | 'OUTBOUND';
  cargo_risk_level: RiskLevel;
  eta?: string;
}

export interface CommandCenterFilters {
  industry?: string;
  riskLevel?: RiskLevel;
  timeWindow?: '24h' | '7d' | '30d';
  port?: string;
  startDate?: string;
  endDate?: string;
}

export interface TimelineEvent {
  date: string;
  event: string;
  type: 'entity' | 'relationship' | 'shipment' | 'alert';
}

export interface CommandCenterState {
  selectedLens: AnalyticalLens;
  corridors: RiskCorridor[];
  selectedCorridor?: RiskCorridor;
  selectedVessel?: Vessel;
  vessels: Vessel[];
  timeline: TimelineEvent[];
  filters: CommandCenterFilters;
  loading: boolean;
  error?: string;
  autoRotationEnabled: boolean;
  currentRotationIndex: number;
  availableIndustries: string[];
  replayState?: {
    currentDate: Date;
    isPlaying: boolean;
    speed: 1 | 2 | 5;
    selectedNode?: string;
  };
}

interface CommandCenterContextType {
  state: CommandCenterState;
  switchLens: (lens: AnalyticalLens) => void;
  setCorridor: (corridor: RiskCorridor | undefined) => void;
  setVessel: (vessel: Vessel | undefined) => void;
  setFilters: (filters: Partial<CommandCenterFilters>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error?: string) => void;
  setCorridors: (corridors: RiskCorridor[]) => void;
  setVessels: (vessels: Vessel[]) => void;
  setReplayTimeline: (timeline: TimelineEvent[]) => void;
  updateReplayState: (state: Partial<CommandCenterState['replayState']>) => void;
  setAutoRotationEnabled: (enabled: boolean) => void;
  setCurrentRotationIndex: (index: number) => void;
}

const CommandCenterContext = createContext<CommandCenterContextType | undefined>(undefined);

export function CommandCenterProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<CommandCenterState>({
    selectedLens: 'case',
    corridors: [],
    vessels: [],
    timeline: [],
    filters: {
      timeWindow: '7d',
    },
    loading: false,
    autoRotationEnabled: true,
    currentRotationIndex: 0,
    availableIndustries: [],
  });

  const switchLens = (lens: AnalyticalLens) => {
    setState(prev => ({ ...prev, selectedLens: lens }));
  };

  const setCorridor = (corridor: RiskCorridor | undefined) => {
    setState(prev => ({ ...prev, selectedCorridor: corridor }));
  };

  const setVessel = (vessel: Vessel | undefined) => {
    setState(prev => ({ ...prev, selectedVessel: vessel }));
  };

  const setFilters = (filters: Partial<CommandCenterFilters>) => {
    setState(prev => ({
      ...prev,
      filters: { ...prev.filters, ...filters },
    }));
  };

  const setLoading = (loading: boolean) => {
    setState(prev => ({ ...prev, loading }));
  };

  const setError = (error?: string) => {
    setState(prev => ({ ...prev, error }));
  };

  const setCorridors = (corridors: RiskCorridor[]) => {
    setState(prev => ({ ...prev, corridors }));
  };

  const setVessels = (vessels: Vessel[]) => {
    setState(prev => ({ ...prev, vessels }));
  };

  const setReplayTimeline = (timeline: TimelineEvent[]) => {
    setState(prev => ({ ...prev, timeline }));
  };

  const updateReplayState = (replayState: Partial<CommandCenterState['replayState']>) => {
    setState(prev => ({
      ...prev,
      replayState: { ...prev.replayState, ...replayState } as any,
    }));
  };

  const setAutoRotationEnabled = (enabled: boolean) => {
    setState(prev => ({ ...prev, autoRotationEnabled: enabled }));
  };

  const setCurrentRotationIndex = (index: number) => {
    setState(prev => ({ ...prev, currentRotationIndex: index }));
  };

  const contextValue = useMemo(
    () => ({
      state,
      switchLens,
      setCorridor,
      setVessel,
      setFilters,
      setLoading,
      setError,
      setCorridors,
      setVessels,
      setReplayTimeline,
      updateReplayState,
      setAutoRotationEnabled,
      setCurrentRotationIndex,
    }),
    [state]
  );

  return (
    <CommandCenterContext.Provider value={contextValue}>
      {children}
    </CommandCenterContext.Provider>
  );
}

export function useCommandCenter() {
  const context = useContext(CommandCenterContext);
  if (!context) {
    throw new Error('useCommandCenter must be used within CommandCenterProvider');
  }
  return context;
}
