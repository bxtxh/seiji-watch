import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Observability Data Collection API
 * 
 * Receives monitoring data from the frontend and processes it for analysis.
 * In a production environment, this would forward data to a monitoring service
 * like DataDog, New Relic, or a custom analytics platform.
 */

interface ObservabilityData {
  sessionId: string;
  timestamp: number;
  metrics: Array<{
    name: string;
    value: number;
    timestamp: number;
    tags?: Record<string, string>;
  }>;
  errors: Array<{
    error: {
      message: string;
      stack?: string;
    };
    context?: string;
    userId?: string;
    sessionId?: string;
    timestamp: number;
    userAgent?: string;
    url?: string;
    additionalData?: Record<string, any>;
  }>;
  interactions: Array<{
    type: string;
    element?: string;
    value?: string;
    timestamp: number;
    sessionId?: string;
    pageUrl: string;
  }>;
  webVitals: {
    fcp?: number;
    lcp?: number;
    fid?: number;
    cls?: number;
    ttfb?: number;
  };
  userAgent: string;
  url: string;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Only accept POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const data: ObservabilityData = req.body;

    // Validate required fields
    if (!data.sessionId || !data.timestamp) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Process the observability data
    await processObservabilityData(data, req);

    res.status(200).json({ 
      success: true, 
      timestamp: Date.now(),
      processed: {
        metrics: data.metrics.length,
        errors: data.errors.length,
        interactions: data.interactions.length
      }
    });

  } catch (error) {
    console.error('Failed to process observability data:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}

async function processObservabilityData(data: ObservabilityData, req: NextApiRequest) {
  const clientIP = req.headers['x-forwarded-for'] || req.connection.remoteAddress;
  const timestamp = new Date().toISOString();

  // Log structured data for analysis
  const logEntry = {
    timestamp,
    sessionId: data.sessionId,
    clientIP,
    userAgent: data.userAgent,
    url: data.url,
    summary: {
      metricsCount: data.metrics.length,
      errorsCount: data.errors.length,
      interactionsCount: data.interactions.length,
      webVitals: data.webVitals
    }
  };

  // In development, log to console
  if (process.env.NODE_ENV === 'development') {
    console.log('[Observability]', JSON.stringify(logEntry, null, 2));
    
    // Log individual metrics for debugging
    data.metrics.forEach(metric => {
      console.log(`[Metric] ${metric.name}: ${metric.value}${metric.tags ? ` (${JSON.stringify(metric.tags)})` : ''}`);
    });

    // Log errors
    data.errors.forEach(error => {
      console.error(`[Error] ${error.context}: ${error.error.message}`);
    });
  }

  // Process metrics
  await processMetrics(data.metrics, data.sessionId);

  // Process errors
  await processErrors(data.errors, data.sessionId);

  // Process interactions
  await processInteractions(data.interactions, data.sessionId);

  // Process Web Vitals
  await processWebVitals(data.webVitals, data.sessionId);
}

async function processMetrics(metrics: ObservabilityData['metrics'], sessionId: string) {
  // Group metrics by name for analysis
  const metricsByName = metrics.reduce((acc, metric) => {
    if (!acc[metric.name]) {
      acc[metric.name] = [];
    }
    acc[metric.name].push(metric);
    return acc;
  }, {} as Record<string, typeof metrics>);

  // Analyze each metric type
  for (const [name, metricList] of Object.entries(metricsByName)) {
    const values = metricList.map(m => m.value);
    const analysis = {
      name,
      count: values.length,
      min: Math.min(...values),
      max: Math.max(...values),
      avg: values.reduce((a, b) => a + b, 0) / values.length,
      sessionId
    };

    // Log analysis for monitoring
    console.log(`[Metric Analysis] ${name}:`, analysis);

    // In production, you would send this to your monitoring service
    // Example: await sendToDataDog(analysis);
    // Example: await sendToNewRelic(analysis);
  }
}

async function processErrors(errors: ObservabilityData['errors'], sessionId: string) {
  for (const error of errors) {
    // Create error report
    const errorReport = {
      timestamp: new Date().toISOString(),
      sessionId,
      message: error.error.message,
      stack: error.error.stack,
      context: error.context,
      url: error.url,
      userAgent: error.userAgent,
      additionalData: error.additionalData
    };

    // Log error for monitoring
    console.error('[Error Report]', errorReport);

    // In production, you would send this to your error tracking service
    // Example: await sendToSentry(errorReport);
    // Example: await sendToBugsnag(errorReport);
  }
}

async function processInteractions(interactions: ObservabilityData['interactions'], sessionId: string) {
  // Analyze user behavior patterns
  const interactionsByType = interactions.reduce((acc, interaction) => {
    if (!acc[interaction.type]) {
      acc[interaction.type] = [];
    }
    acc[interaction.type].push(interaction);
    return acc;
  }, {} as Record<string, typeof interactions>);

  // Log interaction analysis
  for (const [type, interactionList] of Object.entries(interactionsByType)) {
    console.log(`[Interaction Analysis] ${type}: ${interactionList.length} events`);
  }

  // Track search patterns
  const searches = interactions.filter(i => i.type === 'search');
  if (searches.length > 0) {
    const searchAnalysis = {
      totalSearches: searches.length,
      uniqueQueries: new Set(searches.map(s => s.value)).size,
      averageQueryLength: searches.reduce((sum, s) => sum + (s.value?.length || 0), 0) / searches.length,
      sessionId
    };
    console.log('[Search Analysis]', searchAnalysis);
  }
}

async function processWebVitals(webVitals: ObservabilityData['webVitals'], sessionId: string) {
  // Analyze Core Web Vitals
  const vitalsAnalysis = {
    sessionId,
    timestamp: new Date().toISOString(),
    vitals: webVitals,
    ratings: {
      fcp: webVitals.fcp ? getRating(webVitals.fcp, [1800, 3000]) : null,
      lcp: webVitals.lcp ? getRating(webVitals.lcp, [2500, 4000]) : null,
      fid: webVitals.fid ? getRating(webVitals.fid, [100, 300]) : null,
      cls: webVitals.cls ? getRating(webVitals.cls, [0.1, 0.25]) : null,
      ttfb: webVitals.ttfb ? getRating(webVitals.ttfb, [800, 1800]) : null
    }
  };

  console.log('[Web Vitals Analysis]', vitalsAnalysis);

  // Alert on poor Core Web Vitals
  const poorVitals = Object.entries(vitalsAnalysis.ratings)
    .filter(([_, rating]) => rating === 'poor')
    .map(([vital, _]) => vital);

  if (poorVitals.length > 0) {
    console.warn(`[Performance Alert] Poor Core Web Vitals detected: ${poorVitals.join(', ')} for session ${sessionId}`);
  }
}

function getRating(value: number, thresholds: [number, number]): 'good' | 'needs-improvement' | 'poor' {
  if (value <= thresholds[0]) return 'good';
  if (value <= thresholds[1]) return 'needs-improvement';
  return 'poor';
}