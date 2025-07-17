// Service Worker for Diet Issue Tracker PWA
// Implements caching strategies for offline functionality

const CACHE_NAME = "diet-tracker-v1.0.0";
const STATIC_CACHE_NAME = "diet-tracker-static-v1.0.0";
const API_CACHE_NAME = "diet-tracker-api-v1.0.0";

// Resources to cache on install
const STATIC_RESOURCES = [
  "/",
  "/manifest.json",
  "/_next/static/css/app.css",
  "/_next/static/chunks/main.js",
  "/_next/static/chunks/pages/_app.js",
  "/_next/static/chunks/pages/index.js",
  "/offline.html",
];

// API endpoints to cache
const API_ENDPOINTS = ["/api/health", "/search", "/voting/stats"];

// Install event - cache static resources
self.addEventListener("install", (event) => {
  console.log("[SW] Installing Service Worker...");

  event.waitUntil(
    (async () => {
      try {
        // Cache static resources
        const staticCache = await caches.open(STATIC_CACHE_NAME);
        await staticCache.addAll(STATIC_RESOURCES);

        console.log("[SW] Static resources cached successfully");

        // Skip waiting to activate immediately
        self.skipWaiting();
      } catch (error) {
        console.error("[SW] Error during install:", error);
      }
    })(),
  );
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
  console.log("[SW] Activating Service Worker...");

  event.waitUntil(
    (async () => {
      try {
        // Get all cache names
        const cacheNames = await caches.keys();

        // Delete old caches
        const deletePromises = cacheNames
          .filter((cacheName) => {
            return (
              cacheName !== STATIC_CACHE_NAME &&
              cacheName !== API_CACHE_NAME &&
              cacheName !== CACHE_NAME
            );
          })
          .map((cacheName) => {
            console.log("[SW] Deleting old cache:", cacheName);
            return caches.delete(cacheName);
          });

        await Promise.all(deletePromises);

        // Take control of all clients
        await self.clients.claim();

        console.log("[SW] Service Worker activated successfully");
      } catch (error) {
        console.error("[SW] Error during activation:", error);
      }
    })(),
  );
});

// Fetch event - implement caching strategies
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") {
    return;
  }

  // Skip chrome-extension and other protocols
  if (!url.protocol.startsWith("http")) {
    return;
  }

  // Skip external API requests (API Gateway on different port)
  if (url.origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    (async () => {
      try {
        // Strategy 1: API requests - Network First with fallback
        if (isApiRequest(url)) {
          return await networkFirstStrategy(request);
        }

        // Strategy 2: Static resources - Cache First
        if (isStaticResource(url)) {
          return await cacheFirstStrategy(request);
        }

        // Strategy 3: HTML pages - Network First with offline fallback
        if (isHtmlRequest(request)) {
          return await networkFirstWithOfflineFallback(request);
        }

        // Strategy 4: Other resources - Network First
        return await networkFirstStrategy(request);
      } catch (error) {
        console.error("[SW] Error in fetch handler:", error);

        // Fallback to offline page for navigation requests
        if (request.mode === "navigate") {
          const offlineCache = await caches.open(STATIC_CACHE_NAME);
          return (
            (await offlineCache.match("/offline.html")) ||
            new Response("Offline")
          );
        }

        return new Response("Network error", { status: 503 });
      }
    })(),
  );
});

// Helper functions for request classification
function isApiRequest(url) {
  // Only handle internal API routes, exclude external API Gateway
  return (
    url.origin === self.location.origin &&
    (url.pathname.startsWith("/api/") ||
      url.pathname.startsWith("/search") ||
      url.pathname.startsWith("/voting/") ||
      url.pathname.startsWith("/health"))
  );
}

function isStaticResource(url) {
  return (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/static/") ||
    url.pathname.includes(".css") ||
    url.pathname.includes(".js") ||
    url.pathname.includes(".woff") ||
    url.pathname.includes(".png") ||
    url.pathname.includes(".jpg") ||
    url.pathname.includes(".svg") ||
    url.pathname === "/manifest.json"
  );
}

function isHtmlRequest(request) {
  return (
    request.mode === "navigate" ||
    request.headers.get("accept")?.includes("text/html")
  );
}

// Caching strategies
async function networkFirstStrategy(request) {
  try {
    // Try network first
    const networkResponse = await fetch(request);

    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(API_CACHE_NAME);
      cache.put(request.clone(), networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    // Fallback to cache
    console.log("[SW] Network failed, trying cache:", request.url);
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    throw error;
  }
}

async function cacheFirstStrategy(request) {
  // Try cache first
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  // Fallback to network
  try {
    const networkResponse = await fetch(request);

    // Cache the response
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request.clone(), networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.error("[SW] Both cache and network failed for:", request.url);
    throw error;
  }
}

async function networkFirstWithOfflineFallback(request) {
  try {
    // Try network first
    const networkResponse = await fetch(request);

    // Cache successful HTML responses
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request.clone(), networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    // Try cache
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    // Fallback to offline page
    console.log("[SW] Serving offline page for:", request.url);
    const offlineCache = await caches.open(STATIC_CACHE_NAME);
    return (
      (await offlineCache.match("/offline.html")) ||
      new Response("Offline", { status: 503 })
    );
  }
}

// Background sync for form submissions when online
self.addEventListener("sync", (event) => {
  console.log("[SW] Background sync event:", event.tag);

  if (event.tag === "search-sync") {
    event.waitUntil(syncPendingSearches());
  }
});

async function syncPendingSearches() {
  try {
    // Implementation for syncing pending searches when back online
    console.log("[SW] Syncing pending searches...");

    // Get pending searches from IndexedDB (if implemented)
    // Send them to the server
    // Clear pending searches
  } catch (error) {
    console.error("[SW] Error syncing searches:", error);
  }
}

// Push notification handler (for future use)
self.addEventListener("push", (event) => {
  console.log("[SW] Push notification received:", event);

  const options = {
    body: event.data ? event.data.text() : "新しい国会情報が更新されました",
    icon: "/icon-192x192.png",
    badge: "/icon-192x192.png",
    tag: "diet-update",
    data: {
      url: "/",
    },
    actions: [
      {
        action: "view",
        title: "確認する",
        icon: "/icon-192x192.png",
      },
      {
        action: "dismiss",
        title: "閉じる",
      },
    ],
    requireInteraction: false,
    silent: false,
  };

  event.waitUntil(
    self.registration.showNotification("国会議事録検索システム", options),
  );
});

// Notification click handler
self.addEventListener("notificationclick", (event) => {
  console.log("[SW] Notification clicked:", event);

  event.notification.close();

  if (event.action === "view") {
    event.waitUntil(clients.openWindow(event.notification.data.url || "/"));
  }
});

// Message handler for communication with main thread
self.addEventListener("message", (event) => {
  console.log("[SW] Message received:", event.data);

  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }

  if (event.data && event.data.type === "GET_CACHE_STATUS") {
    getCacheStatus().then((status) => {
      event.ports[0].postMessage({ type: "CACHE_STATUS", data: status });
    });
  }
});

async function getCacheStatus() {
  try {
    const cacheNames = await caches.keys();
    const status = {
      totalCaches: cacheNames.length,
      caches: {},
    };

    for (const cacheName of cacheNames) {
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      status.caches[cacheName] = keys.length;
    }

    return status;
  } catch (error) {
    console.error("[SW] Error getting cache status:", error);
    return { error: error.message };
  }
}

console.log("[SW] Service Worker script loaded");
