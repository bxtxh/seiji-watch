/**
 * Security Context for managing CSRF tokens and security state
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { CSRFProtection, generateSecureId } from '@/utils/security';

interface SecurityContextType {
  csrfToken: string | null;
  sessionId: string | null;
  refreshCSRFToken: () => string;
  validateCSRFToken: (token: string) => boolean;
  consumeCSRFToken: (token: string) => boolean;
  isSecurityReady: boolean;
}

const SecurityContext = createContext<SecurityContextType | undefined>(undefined);

interface SecurityProviderProps {
  children: ReactNode;
}

export function SecurityProvider({ children }: SecurityProviderProps) {
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSecurityReady, setIsSecurityReady] = useState(false);

  // Initialize security on mount
  useEffect(() => {
    // Generate session ID
    const newSessionId = generateSecureId(32);
    setSessionId(newSessionId);

    // Generate initial CSRF token
    const initialToken = CSRFProtection.generateToken();
    setCsrfToken(initialToken);

    setIsSecurityReady(true);

    // Clean up on unmount
    return () => {
      setIsSecurityReady(false);
    };
  }, []);

  // Refresh CSRF token every 30 minutes
  useEffect(() => {
    if (!isSecurityReady) return;

    const refreshInterval = setInterval(() => {
      const newToken = CSRFProtection.generateToken();
      setCsrfToken(newToken);
    }, 30 * 60 * 1000); // 30 minutes

    return () => clearInterval(refreshInterval);
  }, [isSecurityReady]);

  const refreshCSRFToken = (): string => {
    const newToken = CSRFProtection.generateToken();
    setCsrfToken(newToken);
    return newToken;
  };

  const validateCSRFToken = (token: string): boolean => {
    return CSRFProtection.validateToken(token);
  };

  const consumeCSRFToken = (token: string): boolean => {
    const isValid = CSRFProtection.consumeToken(token);
    if (isValid) {
      // Generate new token after consumption
      refreshCSRFToken();
    }
    return isValid;
  };

  const value: SecurityContextType = {
    csrfToken,
    sessionId,
    refreshCSRFToken,
    validateCSRFToken,
    consumeCSRFToken,
    isSecurityReady,
  };

  return (
    <SecurityContext.Provider value={value}>
      {children}
    </SecurityContext.Provider>
  );
}

export function useSecurityContext(): SecurityContextType {
  const context = useContext(SecurityContext);
  if (context === undefined) {
    throw new Error('useSecurityContext must be used within a SecurityProvider');
  }
  return context;
}

// Higher-order component for protecting components
export function withSecurityContext<P extends object>(
  Component: React.ComponentType<P>
): React.ComponentType<P> {
  return function SecuredComponent(props: P) {
    const security = useSecurityContext();
    
    if (!security.isSecurityReady) {
      return (
        <div className="flex items-center justify-center p-4">
          <div className="text-sm text-gray-600">セキュリティの初期化中...</div>
        </div>
      );
    }

    return <Component {...props} />;
  };
}

// Hook for secure form submission
export function useSecureForm() {
  const security = useSecurityContext();

  const createSecureFormData = (data: Record<string, any>) => {
    if (!security.csrfToken) {
      throw new Error('CSRF token not available');
    }

    return {
      ...data,
      _csrf: security.csrfToken,
      _session: security.sessionId,
    };
  };

  const validateSecureSubmission = (formData: Record<string, any>): boolean => {
    const { _csrf } = formData;
    if (!_csrf || typeof _csrf !== 'string') {
      return false;
    }

    return security.validateCSRFToken(_csrf);
  };

  return {
    createSecureFormData,
    validateSecureSubmission,
    refreshToken: security.refreshCSRFToken,
    isReady: security.isSecurityReady,
  };
}

// Security event logging
export function useSecurityLogger() {
  const security = useSecurityContext();

  const logSecurityEvent = (
    event: 'csrf_validation_failed' | 'rate_limit_exceeded' | 'invalid_input' | 'security_error',
    details?: Record<string, any>
  ) => {
    const logEntry = {
      timestamp: new Date().toISOString(),
      event,
      sessionId: security.sessionId,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
      url: typeof window !== 'undefined' ? window.location.href : 'unknown',
      details: details || {},
    };

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.warn('Security Event:', logEntry);
    }

    // In production, this would send to a security monitoring service
    // TODO: Implement proper security event logging for production
  };

  return { logSecurityEvent };
}

// Security metrics hook
export function useSecurityMetrics() {
  const [metrics, setMetrics] = useState({
    requestsBlocked: 0,
    tokensGenerated: 0,
    validationErrors: 0,
    lastSecurityEvent: null as Date | null,
  });

  const incrementBlocked = () => {
    setMetrics(prev => ({
      ...prev,
      requestsBlocked: prev.requestsBlocked + 1,
      lastSecurityEvent: new Date(),
    }));
  };

  const incrementTokensGenerated = () => {
    setMetrics(prev => ({
      ...prev,
      tokensGenerated: prev.tokensGenerated + 1,
    }));
  };

  const incrementValidationErrors = () => {
    setMetrics(prev => ({
      ...prev,
      validationErrors: prev.validationErrors + 1,
      lastSecurityEvent: new Date(),
    }));
  };

  return {
    metrics,
    incrementBlocked,
    incrementTokensGenerated,
    incrementValidationErrors,
  };
}