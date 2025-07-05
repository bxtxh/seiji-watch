import React, { useState, useEffect } from 'react';
import { CacheManager, getNetworkStatus, isStandaloneMode } from '@/utils/pwa';

interface PWADebugPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function PWADebugPanel({ isOpen, onClose }: PWADebugPanelProps) {
  const [cacheInfo, setCacheInfo] = useState<{ [key: string]: number }>({});
  const [cacheSize, setCacheSize] = useState<number>(0);
  const [networkStatus, setNetworkStatus] = useState<{ online: boolean; connection?: string }>({ online: true, connection: 'unknown' });
  const [swStatus, setSWStatus] = useState<string>('checking');
  const [installPromptAvailable, setInstallPromptAvailable] = useState<boolean>(false);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    // Set client-side flag
    setIsClient(true);
    
    // Initialize network status on client side
    setNetworkStatus(getNetworkStatus());
  }, []);

  useEffect(() => {
    if (!isOpen || !isClient) return;

    // Get cache information
    CacheManager.getCacheInfo().then(setCacheInfo);
    CacheManager.getCacheSize().then(setCacheSize);

    // Check Service Worker status
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready.then((registration) => {
        if (registration.active) {
          setSWStatus('active');
        } else if (registration.installing) {
          setSWStatus('installing');
        } else if (registration.waiting) {
          setSWStatus('waiting');
        }
      }).catch(() => {
        setSWStatus('error');
      });
    } else {
      setSWStatus('unsupported');
    }

    // Check install prompt availability
    setInstallPromptAvailable(!!window.deferredPrompt);

    // Monitor network status
    const handleOnline = () => setNetworkStatus(getNetworkStatus());
    const handleOffline = () => setNetworkStatus(getNetworkStatus());
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [isOpen, isClient]);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleClearCache = async () => {
    const success = await CacheManager.clearCache();
    if (success) {
      setCacheInfo({});
      setCacheSize(0);
      alert('キャッシュがクリアされました');
    } else {
      alert('キャッシュのクリアに失敗しました');
    }
  };

  const handleTriggerInstall = () => {
    if (!isClient) return;
    if (window.deferredPrompt) {
      window.deferredPrompt.prompt();
    } else {
      alert('インストールプロンプトは利用できません');
    }
  };

  const getSwStatusColor = (status: string): string => {
    switch (status) {
      case 'active': return 'text-green-600';
      case 'installing': return 'text-yellow-600';
      case 'waiting': return 'text-blue-600';
      case 'error': return 'text-red-600';
      case 'unsupported': return 'text-gray-600';
      default: return 'text-gray-400';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">PWA デバッグパネル</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* App Status */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">アプリケーション状態</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">表示モード:</span>
                <span className="ml-2">{isClient ? (isStandaloneMode() ? 'スタンドアロン' : 'ブラウザ') : '確認中...'}</span>
              </div>
              <div>
                <span className="font-medium">ネットワーク:</span>
                <span className={`ml-2 ${networkStatus.online ? 'text-green-600' : 'text-red-600'}`}>
                  {networkStatus.online ? 'オンライン' : 'オフライン'}
                </span>
              </div>
              <div>
                <span className="font-medium">接続タイプ:</span>
                <span className="ml-2">{networkStatus.connection}</span>
              </div>
              <div>
                <span className="font-medium">インストール可能:</span>
                <span className={`ml-2 ${installPromptAvailable ? 'text-green-600' : 'text-gray-600'}`}>
                  {installPromptAvailable ? 'はい' : 'いいえ'}
                </span>
              </div>
            </div>
          </div>

          {/* Service Worker Status */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Service Worker</h3>
            <div className="text-sm">
              <span className="font-medium">状態:</span>
              <span className={`ml-2 ${getSwStatusColor(swStatus)}`}>
                {swStatus === 'active' && '稼働中'}
                {swStatus === 'installing' && 'インストール中'}
                {swStatus === 'waiting' && '待機中'}
                {swStatus === 'error' && 'エラー'}
                {swStatus === 'unsupported' && '未サポート'}
                {swStatus === 'checking' && '確認中...'}
              </span>
            </div>
          </div>

          {/* Cache Information */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">キャッシュ情報</h3>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium">総サイズ:</span>
                <span className="ml-2">{formatBytes(cacheSize)}</span>
              </div>
              
              {Object.entries(cacheInfo).map(([cacheName, itemCount]) => (
                <div key={cacheName} className="flex justify-between items-center">
                  <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                    {cacheName}
                  </span>
                  <span>{itemCount} items</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">アクション</h3>
            <div className="space-y-3">
              <button
                onClick={handleClearCache}
                className="w-full bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700 transition-colors"
              >
                キャッシュをクリア
              </button>
              
              {installPromptAvailable && (
                <button
                  onClick={handleTriggerInstall}
                  className="w-full bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 transition-colors"
                >
                  インストールプロンプトを表示
                </button>
              )}
              
              <button
                onClick={() => {
                  if (isClient) {
                    window.location.reload();
                  }
                }}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors"
              >
                ページを再読み込み
              </button>
              
              <button
                onClick={() => {
                  if (isClient && 'serviceWorker' in navigator) {
                    navigator.serviceWorker.getRegistrations().then((registrations) => {
                      registrations.forEach((registration) => {
                        registration.unregister();
                      });
                      alert('Service Worker の登録を解除しました');
                    });
                  }
                }}
                className="w-full bg-gray-600 text-white py-2 px-4 rounded hover:bg-gray-700 transition-colors"
              >
                Service Worker の登録解除
              </button>
            </div>
          </div>

          {/* Debug Information */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">デバッグ情報</h3>
            <div className="text-xs bg-gray-100 p-3 rounded font-mono overflow-x-auto">
              {isClient ? (
                <>
                  <div>User Agent: {navigator.userAgent}</div>
                  <div>Viewport: {window.innerWidth} × {window.innerHeight}</div>
                  <div>Screen: {screen.width} × {screen.height}</div>
                  <div>Device Pixel Ratio: {window.devicePixelRatio}</div>
                  <div>Language: {navigator.language}</div>
                  <div>Platform: {navigator.platform}</div>
                  <div>Cache Support: {'caches' in window ? 'Yes' : 'No'}</div>
                  <div>Service Worker Support: {'serviceWorker' in navigator ? 'Yes' : 'No'}</div>
                  <div>Push Support: {'PushManager' in window ? 'Yes' : 'No'}</div>
                  <div>Notification Support: {'Notification' in window ? 'Yes' : 'No'}</div>
                </>
              ) : (
                <div>デバッグ情報を読み込み中...</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}