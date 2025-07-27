import React, { createContext, useContext, useState, useCallback, useRef } from 'react';

// Type definitions
export interface WebVitals {
  fcp?: number;  // First Contentful Paint
  lcp?: number;  // Largest Contentful Paint
  fid?: number;  // First Input Delay
  cls?: number;  // Cumulative Layout Shift
  ttfb?: number; // Time to First Byte
}

export interface SessionSummary {
  sessionId: string;
  metricsCount: number;
  errorsCount: number;
  interactionsCount: number;
}

export interface Metric {
  name: string;
  value: number;
  timestamp: number;
  tags?: Record<string, string>;
}

export interface ErrorRecord {
  error: Error;
  context: string;
  timestamp: number;
  additionalData?: any;
}

export interface Interaction {
  type: string;
  element: string;
  value: string;
}

interface ObservabilityContextType {
  trackEvent: (eventName: string, data?: any) => void;
  trackError: (error: Error) => void;
  trackPageView: (path: string) => void;
  recordPageView: (path: string) => void;
  getWebVitals: () => WebVitals;
  getSessionSummary: () => SessionSummary;
  recordInteraction: (interaction: Interaction) => void;
  recordError: (error: ErrorRecord) => void;
  recordMetric: (metric: Metric) => void;
  startTimer: (name: string) => () => void;
}

// Generate a simple session ID
const generateSessionId = () => {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// Context
const ObservabilityContext = createContext<ObservabilityContextType | null>(null);

// Observability module for staging deployment
export const trackEvent = (eventName: string, data?: any) => {
  console.log(`[Observability] ${eventName}`, data);
};

export const ObservabilityProvider = ({ children }: { children: React.ReactNode }) => {
  const [webVitals, setWebVitals] = useState<WebVitals>({});
  const [sessionSummary, setSessionSummary] = useState<SessionSummary>({
    sessionId: generateSessionId(),
    metricsCount: 0,
    errorsCount: 0,
    interactionsCount: 0,
  });
  
  const timers = useRef<Map<string, number>>(new Map());

  const trackError = useCallback((error: Error) => {
    console.error('[Observability Error]', error);
  }, []);

  const trackPageView = useCallback((path: string) => {
    console.log('[Observability PageView]', path);
  }, []);

  const getWebVitals = useCallback(() => {
    return webVitals;
  }, [webVitals]);

  const getSessionSummary = useCallback(() => {
    return sessionSummary;
  }, [sessionSummary]);

  const recordInteraction = useCallback((interaction: Interaction) => {
    console.log('[Observability Interaction]', interaction);
    setSessionSummary(prev => ({
      ...prev,
      interactionsCount: prev.interactionsCount + 1,
    }));
  }, []);

  const recordError = useCallback((error: ErrorRecord) => {
    console.error('[Observability Error]', error);
    setSessionSummary(prev => ({
      ...prev,
      errorsCount: prev.errorsCount + 1,
    }));
  }, []);

  const recordMetric = useCallback((metric: Metric) => {
    console.log('[Observability Metric]', metric);
    setSessionSummary(prev => ({
      ...prev,
      metricsCount: prev.metricsCount + 1,
    }));
  }, []);

  const startTimer = useCallback((name: string) => {
    const startTime = Date.now();
    timers.current.set(name, startTime);
    
    return () => {
      const endTime = Date.now();
      const duration = endTime - startTime;
      const storedStartTime = timers.current.get(name);
      
      if (storedStartTime) {
        timers.current.delete(name);
        recordMetric({
          name: `timer.${name}`,
          value: duration,
          timestamp: endTime,
        });
      }
    };
  }, [recordMetric]);

  const recordPageView = useCallback((path: string) => {
    console.log('[Observability PageView]', path);
    recordMetric({
      name: 'page_view',
      value: 1,
      timestamp: Date.now(),
      tags: { path },
    });
  }, [recordMetric]);

  // Simulate Web Vitals collection
  React.useEffect(() => {
    // In a real implementation, these would come from performance observers
    const simulateWebVitals = () => {
      setWebVitals({
        fcp: Math.random() * 2000 + 500,    // 500-2500ms
        lcp: Math.random() * 3000 + 1000,   // 1000-4000ms
        fid: Math.random() * 200 + 10,      // 10-210ms
        cls: Math.random() * 0.3,           // 0-0.3
        ttfb: Math.random() * 1500 + 200,   // 200-1700ms
      });
    };

    // Initial simulation
    simulateWebVitals();

    // Update periodically
    const interval = setInterval(simulateWebVitals, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const contextValue: ObservabilityContextType = {
    trackEvent,
    trackError,
    trackPageView,
    recordPageView,
    getWebVitals,
    getSessionSummary,
    recordInteraction,
    recordError,
    recordMetric,
    startTimer,
  };

  return (
    <ObservabilityContext.Provider value={contextValue}>
      {children}
    </ObservabilityContext.Provider>
  );
};

export const useObservability = () => {
  const context = useContext(ObservabilityContext);
  if (!context) {
    // Return a no-op implementation for when the provider is not available
    return {
      trackEvent,
      trackError: (error: Error) => console.error('[Observability Error]', error),
      trackPageView: (path: string) => console.log('[Observability PageView]', path),
      recordPageView: (path: string) => console.log('[Observability PageView]', path),
      getWebVitals: () => ({} as WebVitals),
      getSessionSummary: () => ({
        sessionId: 'no-session',
        metricsCount: 0,
        errorsCount: 0,
        interactionsCount: 0,
      }),
      recordInteraction: (interaction: Interaction) => console.log('[Observability Interaction]', interaction),
      recordError: (error: ErrorRecord) => console.error('[Observability Error]', error),
      recordMetric: (metric: Metric) => console.log('[Observability Metric]', metric),
      startTimer: (name: string) => () => {},
    };
  }
  return context;
};

// Full observability interface for legacy compatibility
export const observability = {
  recordPageView: (path: string) => {
    console.log('[Observability PageView]', path);
  },
  recordMetric: (metric: Metric) => {
    console.log('[Observability Metric]', metric);
  },
  recordError: (error: ErrorRecord) => {
    console.error('[Observability Error]', error);
  },
  recordInteraction: (interaction: Interaction) => {
    console.log('[Observability Interaction]', interaction);
  },
  recordApiCall: (endpoint: string, method: string, duration: number, status: number) => {
    console.log('[Observability API Call]', {
      endpoint,
      method,
      duration,
      status,
      timestamp: Date.now(),
    });
  },
  recordSearch: (query: string, resultCount: number | undefined) => {
    console.log('[Observability Search]', {
      query,
      resultCount: resultCount ?? 0,
      timestamp: Date.now(),
    });
  },
};