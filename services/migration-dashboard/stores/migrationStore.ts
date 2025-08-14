import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

interface MigrationState {
  // Migration Phase
  phase: 1 | 2 | 3
  setPhase: (phase: 1 | 2 | 3) => void
  
  // Status
  status: 'idle' | 'running' | 'stopped' | 'error'
  setStatus: (status: 'idle' | 'running' | 'stopped' | 'error') => void
  
  // Sync Configuration
  syncConfig: {
    mode: 'incremental' | 'full' | 'real_time'
    interval: number
    tables: string[]
  }
  setSyncConfig: (config: Partial<MigrationState['syncConfig']>) => void
  
  // Metrics
  metrics: {
    consistency: number
    syncLag: number
    errorRate: number
    cacheHitRate: number
  }
  updateMetrics: (metrics: Partial<MigrationState['metrics']>) => void
  
  // Feature Flags
  features: {
    supabaseReadEnabled: boolean
    supabaseWriteEnabled: boolean
    airtableFallbackEnabled: boolean
    cacheEnabled: boolean
  }
  toggleFeature: (feature: keyof MigrationState['features']) => void
  
  // Alerts
  alerts: Array<{
    id: string
    severity: 'info' | 'warning' | 'error' | 'critical'
    message: string
    timestamp: string
  }>
  addAlert: (alert: Omit<MigrationState['alerts'][0], 'id' | 'timestamp'>) => void
  removeAlert: (id: string) => void
  clearAlerts: () => void
  
  // Selected Tables
  selectedTables: string[]
  setSelectedTables: (tables: string[]) => void
  
  // Rollback Points
  rollbackPoints: Array<{
    id: string
    phase: number
    description: string
    timestamp: string
    isValid: boolean
  }>
  setRollbackPoints: (points: MigrationState['rollbackPoints']) => void
}

export const useMigrationStore = create<MigrationState>()(
  devtools(
    persist(
      (set) => ({
        // Initial state
        phase: 1,
        status: 'idle',
        syncConfig: {
          mode: 'incremental',
          interval: 5,
          tables: [],
        },
        metrics: {
          consistency: 0,
          syncLag: 0,
          errorRate: 0,
          cacheHitRate: 0,
        },
        features: {
          supabaseReadEnabled: true,
          supabaseWriteEnabled: false,
          airtableFallbackEnabled: true,
          cacheEnabled: true,
        },
        alerts: [],
        selectedTables: [],
        rollbackPoints: [],
        
        // Actions
        setPhase: (phase) => set({ phase }),
        setStatus: (status) => set({ status }),
        
        setSyncConfig: (config) =>
          set((state) => ({
            syncConfig: { ...state.syncConfig, ...config },
          })),
        
        updateMetrics: (metrics) =>
          set((state) => ({
            metrics: { ...state.metrics, ...metrics },
          })),
        
        toggleFeature: (feature) =>
          set((state) => ({
            features: {
              ...state.features,
              [feature]: !state.features[feature],
            },
          })),
        
        addAlert: (alert) =>
          set((state) => ({
            alerts: [
              ...state.alerts,
              {
                ...alert,
                id: Math.random().toString(36).substr(2, 9),
                timestamp: new Date().toISOString(),
              },
            ],
          })),
        
        removeAlert: (id) =>
          set((state) => ({
            alerts: state.alerts.filter((a) => a.id !== id),
          })),
        
        clearAlerts: () => set({ alerts: [] }),
        
        setSelectedTables: (tables) => set({ selectedTables: tables }),
        
        setRollbackPoints: (points) => set({ rollbackPoints: points }),
      }),
      {
        name: 'migration-store',
        partialize: (state) => ({
          phase: state.phase,
          syncConfig: state.syncConfig,
          features: state.features,
          selectedTables: state.selectedTables,
        }),
      }
    )
  )
)