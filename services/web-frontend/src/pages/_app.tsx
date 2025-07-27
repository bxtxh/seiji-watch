import type { AppProps } from "next/app";
import "@/styles/globals.css";
import { useEffect } from "react";
import { useRouter } from "next/router";
import {
  registerServiceWorker,
  setupPWAInstall,
  PWAPerformanceMonitor,
} from "@/utils/pwa";
import { SecurityProvider } from "@/contexts/SecurityContext";
import { observability, ObservabilityProvider } from "@/lib/observability";

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();

  useEffect(() => {
    // Initialize observability on app start
    observability.recordPageView("app_init");

    // Enhanced PWA initialization
    if (typeof window !== "undefined") {
      // Register Service Worker with advanced features
      registerServiceWorker();

      // Setup PWA install prompt
      setupPWAInstall();

      // Performance monitoring
      PWAPerformanceMonitor.measurePageLoad();
      PWAPerformanceMonitor.measureNavigationTiming();

      // Add PWA-specific styles
      if (
        window.matchMedia &&
        window.matchMedia("(display-mode: standalone)").matches
      ) {
        document.body.classList.add("standalone-mode");
        observability.recordMetric({
          name: "pwa.standalone_mode",
          value: 1,
          timestamp: Date.now(),
          tags: { mode: "standalone" },
        });
      }

      // Handle network status changes
      const handleOnline = () => {
        console.log("App is online");
        observability.recordMetric({
          name: "network.status_change",
          value: 1,
          timestamp: Date.now(),
          tags: { status: "online" },
        });

        // Remove offline indicators
        const offlineIndicators =
          document.querySelectorAll(".offline-indicator");
        offlineIndicators.forEach((indicator) => indicator.remove());
      };

      const handleOffline = () => {
        console.log("App is offline");
        observability.recordMetric({
          name: "network.status_change",
          value: 1,
          timestamp: Date.now(),
          tags: { status: "offline" },
        });

        observability.recordError({
          error: new Error("Network went offline"),
          context: "network_status",
          timestamp: Date.now(),
        });
      };

      window.addEventListener("online", handleOnline);
      window.addEventListener("offline", handleOffline);

      // Global error handling for unhandled errors
      const handleGlobalError = (event: ErrorEvent) => {
        observability.recordError({
          error: new Error(event.message),
          context: "global_error",
          timestamp: Date.now(),
          additionalData: {
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
          },
        });
      };

      window.addEventListener("error", handleGlobalError);

      // Cleanup event listeners
      return () => {
        window.removeEventListener("online", handleOnline);
        window.removeEventListener("offline", handleOffline);
        window.removeEventListener("error", handleGlobalError);
      };
    }
  }, []);

  // Track page views on route changes
  useEffect(() => {
    const handleRouteChange = (url: string) => {
      observability.recordPageView(url);
      observability.recordInteraction({
        type: "navigation",
        element: "router",
        value: url,
      });
    };

    router.events.on("routeChangeComplete", handleRouteChange);

    return () => {
      router.events.off("routeChangeComplete", handleRouteChange);
    };
  }, [router.events]);

  return (
    <ObservabilityProvider>
      <SecurityProvider>
        <Component {...pageProps} />
      </SecurityProvider>
    </ObservabilityProvider>
  );
}
