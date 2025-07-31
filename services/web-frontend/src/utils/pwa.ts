/**
 * PWA utility functions for Service Worker registration and management
 */

export interface PWAInstallPrompt {
  prompt(): Promise<{ outcome: "accepted" | "dismissed" }>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

declare global {
  interface Window {
    deferredPrompt?: PWAInstallPrompt;
  }
}

/**
 * Register Service Worker
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator)) {
    console.log("Service Worker not supported");
    return null;
  }

  // Skip Service Worker registration in development
  if (process.env.NODE_ENV !== "production") {
    console.log("Service Worker registration skipped in development mode");

    // Unregister any existing Service Worker in development
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (const registration of registrations) {
      await registration.unregister();
      console.log("Unregistered Service Worker:", registration.scope);
    }

    return null;
  }

  try {
    const registration = await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
    });

    console.log("Service Worker registered successfully:", registration.scope);

    // Handle updates
    registration.addEventListener("updatefound", () => {
      const newWorker = registration.installing;
      if (newWorker) {
        newWorker.addEventListener("statechange", () => {
          if (
            newWorker.state === "installed" &&
            navigator.serviceWorker.controller
          ) {
            // New content is available
            showUpdateNotification(registration);
          }
        });
      }
    });

    return registration;
  } catch (error) {
    console.error("Service Worker registration failed:", error);
    return null;
  }
}

/**
 * Show update notification when new SW is available
 */
function showUpdateNotification(registration: ServiceWorkerRegistration) {
  const updateMessage = document.createElement("div");
  updateMessage.className = "pwa-update-notification";

  // Safely create the notification structure without innerHTML
  const notificationDiv = document.createElement("div");
  notificationDiv.className =
    "flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg mb-4";

  // Left side with icon and text
  const leftDiv = document.createElement("div");
  leftDiv.className = "flex items-center";

  const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icon.setAttribute("class", "w-5 h-5 text-blue-600 mr-3");
  icon.setAttribute("fill", "currentColor");
  icon.setAttribute("viewBox", "0 0 20 20");

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("fill-rule", "evenodd");
  path.setAttribute(
    "d",
    "M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
  );
  path.setAttribute("clip-rule", "evenodd");

  icon.appendChild(path);

  const messageSpan = document.createElement("span");
  messageSpan.className = "text-blue-800 font-medium";
  messageSpan.textContent = "新しいバージョンが利用可能です";

  leftDiv.appendChild(icon);
  leftDiv.appendChild(messageSpan);

  // Right side with buttons
  const rightDiv = document.createElement("div");
  rightDiv.className = "flex space-x-2";

  const dismissBtn = document.createElement("button");
  dismissBtn.id = "pwa-update-dismiss";
  dismissBtn.className =
    "text-blue-600 hover:text-blue-800 text-sm font-medium";
  dismissBtn.textContent = "後で";

  const applyBtn = document.createElement("button");
  applyBtn.id = "pwa-update-apply";
  applyBtn.className =
    "bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700";
  applyBtn.textContent = "更新";

  rightDiv.appendChild(dismissBtn);
  rightDiv.appendChild(applyBtn);

  notificationDiv.appendChild(leftDiv);
  notificationDiv.appendChild(rightDiv);
  updateMessage.appendChild(notificationDiv);

  // Insert at the top of the main content
  const main = document.querySelector("main");
  if (main) {
    main.insertBefore(updateMessage, main.firstChild);
  }

  // Handle update actions with direct event listeners (avoid getElementById)
  dismissBtn.addEventListener("click", () => {
    updateMessage.remove();
  });

  applyBtn.addEventListener("click", () => {
    // Tell the new SW to skip waiting
    if (registration.waiting) {
      registration.waiting.postMessage({ type: "SKIP_WAITING" });
    }
    window.location.reload();
  });
}

/**
 * Check for PWA install capability
 */
export function checkPWAInstallability(): boolean {
  // Check if app is already installed
  if (
    window.matchMedia &&
    window.matchMedia("(display-mode: standalone)").matches
  ) {
    return false; // Already installed
  }

  // Check if beforeinstallprompt event is available
  return "onbeforeinstallprompt" in window;
}

/**
 * Setup PWA install prompt
 */
export function setupPWAInstall(): void {
  let deferredPrompt: PWAInstallPrompt | null = null;

  // Listen for the beforeinstallprompt event
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e as unknown as PWAInstallPrompt;

    // Show install button
    showInstallButton(deferredPrompt);
  });

  // Listen for app installed event
  window.addEventListener("appinstalled", () => {
    console.log("PWA was installed");
    hideInstallButton();

    // Track installation
    if (typeof window !== "undefined" && "gtag" in window) {
      (window as any).gtag("event", "pwa_install", {
        event_category: "engagement",
        event_label: "PWA installed",
      });
    }
  });
}

/**
 * Show PWA install button
 */
function showInstallButton(prompt: PWAInstallPrompt): void {
  const installButton = document.createElement("button");
  installButton.id = "pwa-install-button";
  installButton.className =
    "fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg hover:bg-green-700 transition-colors z-50 flex items-center space-x-2";

  // Safely create button content without innerHTML
  const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icon.setAttribute("class", "w-5 h-5");
  icon.setAttribute("fill", "none");
  icon.setAttribute("stroke", "currentColor");
  icon.setAttribute("viewBox", "0 0 24 24");

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  path.setAttribute("stroke-width", "2");
  path.setAttribute("d", "M12 4v16m8-8l-8-8-8 8");

  icon.appendChild(path);

  const span = document.createElement("span");
  span.textContent = "アプリをインストール";

  installButton.appendChild(icon);
  installButton.appendChild(span);

  installButton.addEventListener("click", async () => {
    if (prompt) {
      try {
        await prompt.prompt();
        const choiceResult = await prompt.userChoice;

        if (choiceResult.outcome === "accepted") {
          console.log("User accepted the install prompt");
        } else {
          console.log("User dismissed the install prompt");
        }

        hideInstallButton();
      } catch (error) {
        console.error("Error showing install prompt:", error);
      }
    }
  });

  document.body.appendChild(installButton);

  // Auto-hide after 30 seconds
  setTimeout(() => {
    hideInstallButton();
  }, 30000);
}

/**
 * Hide PWA install button
 */
function hideInstallButton(): void {
  const installButton = document.getElementById("pwa-install-button");
  if (installButton) {
    installButton.remove();
  }
}

/**
 * Check if app is running in standalone mode
 */
export function isStandaloneMode(): boolean {
  return (
    window.matchMedia && window.matchMedia("(display-mode: standalone)").matches
  );
}

/**
 * Get network status
 */
export function getNetworkStatus(): { online: boolean; connection?: string } {
  if (typeof window === "undefined" || !navigator) {
    return { online: true, connection: "unknown" };
  }

  const online = navigator.onLine;
  let connection = "unknown";

  if ("connection" in navigator) {
    const conn = (navigator as any).connection;
    connection = conn.effectiveType || conn.type || "unknown";
  }

  return { online, connection };
}

/**
 * Cache management utilities
 */
export class CacheManager {
  static async getCacheSize(): Promise<number> {
    if (!("caches" in window)) return 0;

    try {
      const cacheNames = await caches.keys();
      let totalSize = 0;

      for (const cacheName of cacheNames) {
        const cache = await caches.open(cacheName);
        const requests = await cache.keys();

        for (const request of requests) {
          const response = await cache.match(request);
          if (response && response.headers.get("content-length")) {
            totalSize += parseInt(
              response.headers.get("content-length") || "0"
            );
          }
        }
      }

      return totalSize;
    } catch (error) {
      console.error("Error calculating cache size:", error);
      return 0;
    }
  }

  static async clearCache(): Promise<boolean> {
    if (!("caches" in window)) return false;

    try {
      const cacheNames = await caches.keys();
      const deletePromises = cacheNames.map((cacheName) =>
        caches.delete(cacheName)
      );
      await Promise.all(deletePromises);

      console.log("All caches cleared");
      return true;
    } catch (error) {
      console.error("Error clearing cache:", error);
      return false;
    }
  }

  static async getCacheInfo(): Promise<{ [key: string]: number }> {
    if (!("caches" in window)) return {};

    try {
      const cacheNames = await caches.keys();
      const info: { [key: string]: number } = {};

      for (const cacheName of cacheNames) {
        const cache = await caches.open(cacheName);
        const keys = await cache.keys();
        info[cacheName] = keys.length;
      }

      return info;
    } catch (error) {
      console.error("Error getting cache info:", error);
      return {};
    }
  }
}

/**
 * Performance monitoring for PWA
 */
export class PWAPerformanceMonitor {
  static measurePageLoad(): void {
    window.addEventListener("load", () => {
      // Measure core web vitals
      if ("PerformanceObserver" in window) {
        // Largest Contentful Paint
        const lcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const lastEntry = entries[entries.length - 1];
          console.log("LCP:", lastEntry.startTime);
        });
        lcpObserver.observe({ entryTypes: ["largest-contentful-paint"] });

        // First Input Delay
        const fidObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            const performanceEntry = entry as any;
            console.log(
              "FID:",
              performanceEntry.processingStart - performanceEntry.startTime
            );
          });
        });
        fidObserver.observe({ entryTypes: ["first-input"] });

        // Cumulative Layout Shift
        const clsObserver = new PerformanceObserver((list) => {
          let clsValue = 0;
          const entries = list.getEntries();
          entries.forEach((entry) => {
            if (!(entry as any).hadRecentInput) {
              clsValue += (entry as any).value;
            }
          });
          console.log("CLS:", clsValue);
        });
        clsObserver.observe({ entryTypes: ["layout-shift"] });
      }
    });
  }

  static measureNavigationTiming(): void {
    window.addEventListener("load", () => {
      const navigation = performance.getEntriesByType(
        "navigation"
      )[0] as PerformanceNavigationTiming;

      console.log("Navigation Timing:", {
        domContentLoaded:
          navigation.domContentLoadedEventEnd -
          navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        ttfb: navigation.responseStart - navigation.requestStart,
      });
    });
  }
}
