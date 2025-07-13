import React, { useEffect, useState } from 'react';

interface PerformanceMetrics {
  loadTime: number;
  domContentLoaded: number;
  firstContentfulPaint: number;
  largestContentfulPaint: number;
  memoryUsage: {
    usedJSHeapSize: number;
    totalJSHeapSize: number;
    jsHeapSizeLimit: number;
  };
  networkRequests: {
    url: string;
    duration: number;
    size: number;
  }[];
}

interface PerformanceMonitorProps {
  isOpen: boolean;
  onClose: () => void;
}

const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({ isOpen, onClose }) => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isOpen) {
      collectMetrics();
      
      // Set up auto-refresh
      const interval = setInterval(collectMetrics, 5000);
      setRefreshInterval(interval);
      
      return () => {
        if (interval) clearInterval(interval);
      };
    }
  }, [isOpen]);

  const collectMetrics = () => {
    try {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      const memory = (performance as any).memory;
      
      const newMetrics: PerformanceMetrics = {
        loadTime: navigation.loadEventEnd - navigation.loadEventStart,
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0,
        largestContentfulPaint: performance.getEntriesByName('largest-contentful-paint')[0]?.startTime || 0,
        memoryUsage: {
          usedJSHeapSize: memory?.usedJSHeapSize || 0,
          totalJSHeapSize: memory?.totalJSHeapSize || 0,
          jsHeapSizeLimit: memory?.jsHeapSizeLimit || 0,
        },
        networkRequests: performance.getEntriesByType('resource')
          .filter(entry => entry.name.includes('/api/'))
          .map(entry => ({
            url: entry.name,
            duration: entry.duration,
            size: (entry as any).transferSize || 0,
          }))
          .slice(-10), // Keep last 10 requests
      };
      
      setMetrics(newMetrics);
    } catch (error) {
      console.error('Error collecting performance metrics:', error);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatTime = (ms: number): string => {
    return ms.toFixed(2) + ' ms';
  };

  const getPerformanceScore = (metric: number, thresholds: { good: number; poor: number }): string => {
    if (metric <= thresholds.good) return 'text-green-600 bg-green-100';
    if (metric <= thresholds.poor) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">パフォーマンス監視ダッシュボード</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {metrics ? (
            <div className="space-y-8">
              {/* Core Web Vitals */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Core Web Vitals</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">Load Time</div>
                    <div className={`text-lg font-semibold px-2 py-1 rounded ${getPerformanceScore(metrics.loadTime, { good: 1000, poor: 2000 })}`}>
                      {formatTime(metrics.loadTime)}
                    </div>
                  </div>
                  
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">DOM Content Loaded</div>
                    <div className={`text-lg font-semibold px-2 py-1 rounded ${getPerformanceScore(metrics.domContentLoaded, { good: 800, poor: 1500 })}`}>
                      {formatTime(metrics.domContentLoaded)}
                    </div>
                  </div>
                  
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">First Contentful Paint</div>
                    <div className={`text-lg font-semibold px-2 py-1 rounded ${getPerformanceScore(metrics.firstContentfulPaint, { good: 1800, poor: 3000 })}`}>
                      {formatTime(metrics.firstContentfulPaint)}
                    </div>
                  </div>
                  
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">Largest Contentful Paint</div>
                    <div className={`text-lg font-semibold px-2 py-1 rounded ${getPerformanceScore(metrics.largestContentfulPaint, { good: 2500, poor: 4000 })}`}>
                      {formatTime(metrics.largestContentfulPaint)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Memory Usage */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">メモリ使用状況</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">使用中</div>
                    <div className="text-lg font-semibold text-blue-600">
                      {formatBytes(metrics.memoryUsage.usedJSHeapSize)}
                    </div>
                  </div>
                  
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">合計</div>
                    <div className="text-lg font-semibold text-green-600">
                      {formatBytes(metrics.memoryUsage.totalJSHeapSize)}
                    </div>
                  </div>
                  
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">制限</div>
                    <div className="text-lg font-semibold text-gray-600">
                      {formatBytes(metrics.memoryUsage.jsHeapSizeLimit)}
                    </div>
                  </div>
                </div>
                
                {/* Memory usage bar */}
                <div className="mt-4">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>メモリ使用率</span>
                    <span>
                      {((metrics.memoryUsage.usedJSHeapSize / metrics.memoryUsage.totalJSHeapSize) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${(metrics.memoryUsage.usedJSHeapSize / metrics.memoryUsage.totalJSHeapSize) * 100}%`
                      }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Network Requests */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">最近のAPIリクエスト</h3>
                <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            URL
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Duration
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Size
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {metrics.networkRequests.length > 0 ? (
                          metrics.networkRequests.map((request, index) => (
                            <tr key={index} className="hover:bg-gray-50">
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {request.url.split('/').pop()}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                <span className={`px-2 py-1 rounded ${getPerformanceScore(request.duration, { good: 500, poor: 1000 })}`}>
                                  {formatTime(request.duration)}
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {formatBytes(request.size)}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={3} className="px-6 py-4 text-center text-sm text-gray-500">
                              APIリクエストがありません
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* Performance Tips */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">パフォーマンス最適化のヒント</h3>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <ul className="text-sm text-blue-800 space-y-2">
                    <li>• 仮想スクロールにより、大量のデータも効率的に表示されます</li>
                    <li>• 日本語検索の最適化により、快適な検索体験を提供します</li>
                    <li>• メモリ使用量を監視し、必要に応じて最適化を行います</li>
                    <li>• APIレスポンス時間を監視し、パフォーマンスを向上させます</li>
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-600">メトリクスを収集中...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PerformanceMonitor;