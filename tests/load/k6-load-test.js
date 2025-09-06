/**
 * K6 Load Testing Suite for Smart Graphic Designer API
 * 
 * This test suite validates the API's performance under various load conditions
 * and ensures SLA compliance for production workloads.
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiResponseTime = new Trend('api_response_time');
const renderSuccessRate = new Rate('render_success_rate');
const costPerRequest = new Trend('cost_per_request');

// Test configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const JWT_TOKEN = __ENV.JWT_TOKEN || 'test-token';
const PROJECT_ID = __ENV.PROJECT_ID || 'load-test-project';

// Load test stages configuration
export const options = {
  stages: [
    // Ramp up
    { duration: '2m', target: 10 },   // Ramp to 10 users over 2 minutes
    { duration: '5m', target: 10 },   // Stay at 10 users for 5 minutes
    { duration: '2m', target: 25 },   // Ramp to 25 users over 2 minutes
    { duration: '5m', target: 25 },   // Stay at 25 users for 5 minutes
    { duration: '2m', target: 50 },   // Ramp to 50 users over 2 minutes
    { duration: '10m', target: 50 },  // Stay at 50 users for 10 minutes
    { duration: '5m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    // Performance SLA thresholds
    'http_req_duration': ['p(95)<1800'],           // 95% of requests under 1.8s (excluding AI generation)
    'http_req_duration{expected_response:true}': ['p(90)<1500'], // 90% of successful requests under 1.5s
    'errors': ['rate<0.05'],                       // Error rate under 5%
    'render_success_rate': ['rate>0.95'],          // Render success rate above 95%
    'api_response_time': ['p(95)<600'],            // 95% of API responses under 600ms (API only, not AI)
    'http_req_failed': ['rate<0.02'],              // Less than 2% failed requests
    'cost_per_request': ['avg<0.10'],              // Average cost per request under $0.10
  },
  // Test scenarios
  scenarios: {
    // Scenario 1: Normal load with various request types
    normal_load: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '5m', target: 20 },
        { duration: '10m', target: 20 },
        { duration: '5m', target: 0 },
      ],
      gracefulRampDown: '30s',
      tags: { scenario: 'normal_load' },
    },
    
    // Scenario 2: Spike testing
    spike_test: {
      executor: 'ramping-vus',
      startTime: '20m',
      startVUs: 1,
      stages: [
        { duration: '30s', target: 100 },  // Quick spike
        { duration: '1m', target: 100 },   // Hold spike
        { duration: '30s', target: 0 },    // Drop quickly
      ],
      gracefulRampDown: '30s',
      tags: { scenario: 'spike_test' },
    },
    
    // Scenario 3: Stress testing for breaking point
    stress_test: {
      executor: 'ramping-vus',
      startTime: '25m',
      startVUs: 1,
      stages: [
        { duration: '2m', target: 50 },
        { duration: '5m', target: 100 },
        { duration: '5m', target: 150 },
        { duration: '5m', target: 200 },
        { duration: '2m', target: 0 },
      ],
      gracefulRampDown: '30s',
      tags: { scenario: 'stress_test' },
    },
  },
};

// Request headers
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${JWT_TOKEN}`,
};

// Test data generators
const generateRenderRequest = (requestType = 'simple') => {
  const baseRequest = {
    project_id: `${PROJECT_ID}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    prompts: {
      task: 'create',
      instruction: '',
    },
    outputs: {
      count: 1,
      format: 'png',
      dimensions: '512x512'
    }
  };
  
  switch (requestType) {
    case 'simple':
      baseRequest.prompts.instruction = 'Create a simple banner with text';
      break;
      
    case 'complex':
      baseRequest.prompts.instruction = 'Create a sophisticated marketing banner with modern typography, gradient backgrounds, and professional layout';
      baseRequest.outputs.count = 3;
      baseRequest.outputs.dimensions = '1200x630';
      baseRequest.constraints = {
        palette_hex: ['#1E3A8A', '#FFFFFF', '#F59E0B'],
        fonts: ['Inter', 'Roboto'],
        logo_safe_zone_pct: 20.0
      };
      break;
      
    case 'bulk':
      baseRequest.prompts.instruction = 'Generate social media assets for product launch';
      baseRequest.outputs.count = 6;
      baseRequest.outputs.dimensions = '1080x1080';
      break;
      
    default:
      baseRequest.prompts.instruction = 'Create a professional design';
  }
  
  return baseRequest;
};

// Test functions
export default function () {
  // Randomly select request type to simulate real usage
  const requestTypes = ['simple', 'simple', 'complex', 'bulk']; // Weighted towards simple
  const requestType = requestTypes[Math.floor(Math.random() * requestTypes.length)];
  
  group('API Health Check', () => {
    const healthResponse = http.get(`${BASE_URL}/healthz`);
    
    check(healthResponse, {
      'health check status is 200': (r) => r.status === 200,
      'health check response time < 200ms': (r) => r.timings.duration < 200,
    });
    
    apiResponseTime.add(healthResponse.timings.duration);
  });
  
  group(`Render Request - ${requestType}`, () => {
    const renderPayload = generateRenderRequest(requestType);
    const startTime = Date.now();
    
    const renderResponse = http.post(
      `${BASE_URL}/render`,
      JSON.stringify(renderPayload),
      { 
        headers,
        timeout: '60s', // Allow time for AI generation
      }
    );
    
    const endTime = Date.now();
    const responseTime = endTime - startTime;
    
    const isSuccess = check(renderResponse, {
      'render request status is 200': (r) => r.status === 200,
      'render response has assets': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.assets && body.assets.length > 0;
        } catch (e) {
          return false;
        }
      },
      'render response has audit info': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.audit && body.audit.trace_id;
        } catch (e) {
          return false;
        }
      },
      'response time acceptable for request type': (r) => {
        const maxTime = requestType === 'bulk' ? 60000 : 
                       requestType === 'complex' ? 30000 : 15000;
        return responseTime < maxTime;
      }
    });
    
    // Record metrics
    renderSuccessRate.add(isSuccess);
    errorRate.add(!isSuccess);
    
    // Extract cost information if available
    if (renderResponse.status === 200) {
      try {
        const body = JSON.parse(renderResponse.body);
        if (body.audit && body.audit.cost_usd) {
          costPerRequest.add(body.audit.cost_usd);
        }
      } catch (e) {
        // Ignore JSON parse errors for metrics
      }
    }
    
    // Add specific checks for different error scenarios
    if (renderResponse.status !== 200) {
      console.log(`Request failed: ${renderResponse.status} - ${renderResponse.body}`);
      
      check(renderResponse, {
        'rate limit response (429)': (r) => r.status === 429,
        'validation error (422)': (r) => r.status === 422,
        'service unavailable (502/503)': (r) => r.status === 502 || r.status === 503,
        'auth error (401)': (r) => r.status === 401,
      });
    }
  });
  
  // Simulate realistic user behavior with think time
  const thinkTime = Math.random() * 3 + 1; // 1-4 seconds
  sleep(thinkTime);
}

// Test lifecycle functions
export function setup() {
  console.log('🚀 Starting load test for SGD API');
  console.log(`📡 Base URL: ${BASE_URL}`);
  console.log(`🔑 Using JWT token: ${JWT_TOKEN ? 'Yes' : 'No'}`);
  
  // Verify API is accessible
  const healthCheck = http.get(`${BASE_URL}/healthz`);
  if (healthCheck.status !== 200) {
    throw new Error(`API not accessible. Health check failed with status: ${healthCheck.status}`);
  }
  
  console.log('✅ API health check passed');
  return {
    baseUrl: BASE_URL,
    startTime: Date.now(),
  };
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`🏁 Load test completed in ${duration.toFixed(2)} seconds`);
  console.log('📊 Check the summary below for detailed metrics');
}

// Helper function for custom scenarios
export function spikeTest() {
  console.log('🔥 Running spike test scenario');
  
  group('Spike Test - Burst Requests', () => {
    const requests = [];
    
    // Create 10 concurrent requests
    for (let i = 0; i < 10; i++) {
      requests.push(['POST', `${BASE_URL}/render`, JSON.stringify(generateRenderRequest('simple')), { headers }]);
    }
    
    const responses = http.batch(requests);
    
    responses.forEach((response, index) => {
      check(response, {
        [`spike request ${index + 1} successful`]: (r) => r.status === 200 || r.status === 429,
      });
    });
  });
}

// Stress test helper
export function stressTest() {
  console.log('💪 Running stress test scenario');
  
  const stressPayload = generateRenderRequest('bulk');
  
  group('Stress Test - Heavy Payload', () => {
    const response = http.post(`${BASE_URL}/render`, JSON.stringify(stressPayload), {
      headers,
      timeout: '120s', // Extended timeout for bulk operations
    });
    
    check(response, {
      'stress test handles heavy load': (r) => r.status === 200 || r.status === 429 || r.status === 503,
      'stress test response time reasonable': (r) => r.timings.duration < 120000,
    });
  });
}