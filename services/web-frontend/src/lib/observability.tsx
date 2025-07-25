import React from 'react';

// Observability module for staging deployment
export const trackEvent = (eventName: string, data?: any) => {
  console.log(`[Observability] ${eventName}`, data);
};

export const ObservabilityProvider = ({ children }: { children: React.ReactNode }) => {
  return <>{children}</>;
};

export const useObservability = () => {
  return {
    trackEvent,
    trackError: (error: Error) => console.error('[Observability Error]', error),
    trackPageView: (path: string) => console.log('[Observability PageView]', path),
  };
};

// Full observability interface for legacy compatibility
export const observability = {
  recordPageView: (path: string) => {
    console.log('[Observability PageView]', path);
  },
  recordMetric: (metric: { name: string; value: number; timestamp: number; tags?: Record<string, string> }) => {
    console.log('[Observability Metric]', metric);
  },
  recordError: (error: { error: Error; context: string; timestamp: number; additionalData?: any }) => {
    console.error('[Observability Error]', error);
  },
  recordInteraction: (interaction: { type: string; element: string; value: string }) => {
    console.log('[Observability Interaction]', interaction);
  },
};