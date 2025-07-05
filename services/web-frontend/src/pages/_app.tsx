import type { AppProps } from 'next/app';
import '@/styles/globals.css';
import { useEffect } from 'react';
import { 
  registerServiceWorker, 
  setupPWAInstall, 
  PWAPerformanceMonitor 
} from '@/utils/pwa';
import { SecurityProvider } from '@/contexts/SecurityContext';

export default function App({ Component, pageProps }: AppProps) {
  useEffect(() => {
    // Enhanced PWA initialization
    if (typeof window !== 'undefined') {
      // Register Service Worker with advanced features
      registerServiceWorker();
      
      // Setup PWA install prompt
      setupPWAInstall();
      
      // Performance monitoring
      PWAPerformanceMonitor.measurePageLoad();
      PWAPerformanceMonitor.measureNavigationTiming();
      
      // Add PWA-specific styles
      if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
        document.body.classList.add('standalone-mode');
      }
      
      // Handle network status changes
      const handleOnline = () => {
        console.log('App is online');
        // Remove offline indicators
        const offlineIndicators = document.querySelectorAll('.offline-indicator');
        offlineIndicators.forEach(indicator => indicator.remove());
      };
      
      const handleOffline = () => {
        console.log('App is offline');
        // Could add offline indicator here
      };
      
      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);
      
      // Cleanup event listeners
      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    }
  }, []);

  return (
    <SecurityProvider>
      <Component {...pageProps} />
    </SecurityProvider>
  );
}