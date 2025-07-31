import React from "react";

const DebugInfo = () => {
  if (process.env.NODE_ENV !== "development") {
    return null;
  }

  const debugInfo = {
    apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "Not set",
    siteName: process.env.NEXT_PUBLIC_SITE_NAME || "Not set",
    enableDebug: process.env.NEXT_PUBLIC_ENABLE_DEBUG || "Not set",
    nodeEnv: process.env.NODE_ENV,
  };

  return (
    <div className="fixed bottom-4 right-4 bg-gray-800 text-white p-4 rounded-lg text-xs max-w-sm">
      <h3 className="font-bold mb-2">Debug Info</h3>
      <div className="space-y-1">
        {Object.entries(debugInfo).map(([key, value]) => (
          <div key={key}>
            <span className="font-semibold">{key}:</span> {value}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DebugInfo;