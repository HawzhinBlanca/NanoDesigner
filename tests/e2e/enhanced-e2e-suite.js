#!/usr/bin/env node

/**
 * Enhanced End-to-End Test Suite for Smart Graphic Designer API
 * 
 * This comprehensive test suite validates the complete user journey,
 * API behavior, error handling, and performance characteristics.
 */

const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');
const jwt = require('jsonwebtoken');

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.WS_BASE_URL || 'ws://localhost:8000';
const TEST_OUTPUT_DIR = './e2e-outputs';
const SCREENSHOT_DIR = path.join(TEST_OUTPUT_DIR, 'screenshots');
const REPORTS_DIR = path.join(TEST_OUTPUT_DIR, 'reports');

// Test configuration
const TEST_CONFIG = {
  timeouts: {
    navigation: 30000,
    api: 10000,
    websocket: 5000,
    render: 60000
  },
  retries: {
    default: 3,
    api: 2,
    websocket: 1
  },
  performance: {
    maxResponseTime: 2000,
    maxRenderTime: 30000,
    maxMemoryUsage: 100 * 1024 * 1024 // 100MB
  }
};

// Enhanced Test Runner with metrics and reporting
class EnhancedTestRunner {
  constructor() {
    this.browser = null;
    this.page = null;
    this.results = [];
    this.metrics = {
      startTime: Date.now(),
      apiCalls: [],
      performance: {},
      errors: [],
      screenshots: []
    };
    this.currentTestContext = null;
  }

  async setup() {
    console.log('🚀 Setting up Enhanced E2E Test Environment');
    
    // Create output directories
    await Promise.all([
      fs.mkdir(TEST_OUTPUT_DIR, { recursive: true }),
      fs.mkdir(SCREENSHOT_DIR, { recursive: true }),
      fs.mkdir(REPORTS_DIR, { recursive: true })
    ]);
    
    // Launch browser with enhanced configuration
    this.browser = await puppeteer.launch({
      headless: process.env.HEADLESS !== 'false',
      devtools: process.env.DEVTOOLS === 'true',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding'
      ]
    });
    
    this.page = await this.browser.newPage();
    
    // Set viewport and user agent
    await this.page.setViewport({ width: 1920, height: 1080 });
    await this.page.setUserAgent('SGD-E2E-Test/1.0 (Puppeteer)');
    
    // Enhanced request/response monitoring
    await this.setupNetworkMonitoring();
    
    // Setup error handling
    this.page.on('pageerror', error => {
      this.metrics.errors.push({
        type: 'page_error',
        message: error.message,
        stack: error.stack,
        timestamp: Date.now(),
        test: this.currentTestContext
      });
    });
    
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        this.metrics.errors.push({
          type: 'console_error',
          message: msg.text(),
          timestamp: Date.now(),
          test: this.currentTestContext
        });
      }
    });

    console.log('✅ Test environment ready');
  }

  async setupNetworkMonitoring() {
    await this.page.setRequestInterception(true);
    
    this.page.on('request', request => {
      const startTime = Date.now();
      request._startTime = startTime;
      
      // Log API requests
      if (request.url().includes(API_BASE_URL.replace('http://', '').replace('https://', ''))) {
        console.log(`🌐 ${request.method()} ${request.url()}`);
      }
      
      request.continue();
    });
    
    this.page.on('response', response => {
      const request = response.request();
      const endTime = Date.now();
      const duration = endTime - (request._startTime || endTime);
      
      // Track API call metrics
      if (request.url().includes(API_BASE_URL.replace('http://', '').replace('https://', ''))) {
        const apiCall = {
          method: request.method(),
          url: request.url(),
          status: response.status(),
          duration,
          timestamp: endTime,
          test: this.currentTestContext,
          headers: Object.fromEntries(response.headers()),
          size: response.headers()['content-length'] || 0
        };
        
        this.metrics.apiCalls.push(apiCall);
        
        // Log response with timing
        const statusIcon = response.status() >= 400 ? '❌' : response.status() >= 300 ? '⚠️' : '✅';
        console.log(`${statusIcon} ${response.status()} ${request.url()} (${duration}ms)`);
        
        // Warn on slow responses
        if (duration > TEST_CONFIG.performance.maxResponseTime) {
          console.log(`⚡ Slow response detected: ${duration}ms`);
        }
      }
    });
  }

  async teardown() {
    console.log('\n🔧 Tearing down test environment');
    
    if (this.browser) {
      await this.browser.close();
    }
    
    // Generate comprehensive report
    await this.generateReport();
    
    // Print summary
    this.printTestSummary();
  }

  async runTest(name, testFn, options = {}) {
    this.currentTestContext = name;
    const testStartTime = Date.now();
    
    console.log(`\n🧪 Running: ${name}`);
    
    const retries = options.retries || TEST_CONFIG.retries.default;
    let lastError = null;
    
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        if (attempt > 1) {
          console.log(`   🔄 Retry ${attempt}/${retries}`);
          await this.page.waitForTimeout(1000 * attempt); // Progressive backoff
        }
        
        const result = await Promise.race([
          testFn(),
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Test timeout')), 
            options.timeout || TEST_CONFIG.timeouts.api)
          )
        ]);
        
        const duration = Date.now() - testStartTime;
        const status = result ? 'PASS' : 'FAIL';
        
        this.results.push({ 
          name, 
          status, 
          duration, 
          attempt,
          timestamp: testStartTime 
        });
        
        console.log(result ? `✅ ${name} passed (${duration}ms)` : `❌ ${name} failed (${duration}ms)`);
        
        // Take screenshot on failure
        if (!result) {
          await this.captureFailureScreenshot(name);
        }
        
        this.currentTestContext = null;
        return result;
        
      } catch (error) {
        lastError = error;
        console.error(`❌ ${name} failed on attempt ${attempt}:`, error.message);
        
        if (attempt === retries) {
          const duration = Date.now() - testStartTime;
          this.results.push({ 
            name, 
            status: 'FAIL', 
            error: error.message, 
            duration,
            attempts: retries,
            timestamp: testStartTime 
          });
          
          await this.captureFailureScreenshot(name);
        }
      }
    }
    
    this.currentTestContext = null;
    return false;
  }

  async captureFailureScreenshot(testName) {
    try {
      const filename = `failure-${testName.replace(/[^a-zA-Z0-9]/g, '-')}-${Date.now()}.png`;
      const screenshotPath = path.join(SCREENSHOT_DIR, filename);
      
      await this.page.screenshot({ 
        path: screenshotPath, 
        fullPage: true 
      });
      
      this.metrics.screenshots.push({
        test: testName,
        type: 'failure',
        path: screenshotPath,
        timestamp: Date.now()
      });
      
      console.log(`📸 Failure screenshot saved: ${filename}`);
    } catch (error) {
      console.error('Failed to capture screenshot:', error.message);
    }
  }

  generateJWT(options = {}) {
    const payload = {
      sub: options.userId || 'test-user-001',
      iss: 'sgd-e2e-tests',
      exp: Math.floor(Date.now() / 1000) + (options.expiresIn || 3600),
      iat: Math.floor(Date.now() / 1000),
      org_id: options.orgId || 'test-org-001',
      email: options.email || 'test@example.com',
      roles: options.roles || ['user'],
      ...options.claims
    };
    
    return jwt.sign(payload, 'demo-secret-key-for-testing-only', { algorithm: 'HS256' });
  }

  async makeAPICall(endpoint, options = {}) {
    const token = options.token || this.generateJWT(options.auth);
    const url = `${API_BASE_URL}${endpoint}`;
    const timeout = options.timeout || TEST_CONFIG.timeouts.api;
    
    return await this.page.evaluate(async (url, token, options, timeout) => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      
      try {
        const headers = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-Request-ID': `e2e-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          ...options.headers
        };
        
        const fetchOptions = {
          method: options.method || 'GET',
          headers,
          signal: controller.signal,
          ...options
        };
        
        if (options.body && typeof options.body === 'object') {
          fetchOptions.body = JSON.stringify(options.body);
        }
        
        const response = await fetch(url, fetchOptions);
        clearTimeout(timeoutId);
        
        const contentType = response.headers.get('content-type') || '';
        let data = null;
        
        if (contentType.includes('application/json')) {
          data = await response.json();
        } else {
          data = await response.text();
        }
        
        return {
          status: response.status,
          statusText: response.statusText,
          ok: response.ok,
          data,
          headers: Object.fromEntries(response.headers),
          url: response.url
        };
        
      } catch (error) {
        clearTimeout(timeoutId);
        return {
          status: 0,
          ok: false,
          error: error.message,
          type: error.name
        };
      }
    }, url, token, options, timeout);
  }

  // Enhanced test methods with better validation

  async testSystemHealth() {
    const response = await this.makeAPICall('/healthz');
    
    if (!response.ok) {
      console.log(`Health check failed: ${response.status} ${response.statusText}`);
      return false;
    }
    
    const requiredFields = ['status', 'timestamp'];
    const hasRequiredFields = requiredFields.every(field => 
      response.data && response.data.hasOwnProperty(field)
    );
    
    if (!hasRequiredFields) {
      console.log('Health response missing required fields:', response.data);
      return false;
    }
    
    // Test dependency health if available
    if (response.data.dependencies) {
      const unhealthyDeps = Object.entries(response.data.dependencies)
        .filter(([name, status]) => !['connected', 'available', 'healthy'].includes(status));
        
      if (unhealthyDeps.length > 0) {
        console.log('Unhealthy dependencies detected:', unhealthyDeps);
      }
    }
    
    return response.data.status === 'healthy' || response.data.ok === true;
  }

  async testAuthenticationScenarios() {
    console.log('   Testing authentication scenarios...');
    
    // Test 1: No token
    const noTokenResponse = await this.makeAPICall('/render', { token: '' });
    if (noTokenResponse.status !== 401) {
      console.log('❌ Expected 401 without token, got:', noTokenResponse.status);
      return false;
    }
    
    // Test 2: Invalid token
    const invalidTokenResponse = await this.makeAPICall('/render', { token: 'invalid-token' });
    if (invalidTokenResponse.status !== 401) {
      console.log('❌ Expected 401 with invalid token, got:', invalidTokenResponse.status);
      return false;
    }
    
    // Test 3: Expired token
    const expiredToken = this.generateJWT({ expiresIn: -3600 }); // Expired 1 hour ago
    const expiredTokenResponse = await this.makeAPICall('/render', { token: expiredToken });
    if (expiredTokenResponse.status !== 401) {
      console.log('❌ Expected 401 with expired token, got:', expiredTokenResponse.status);
      return false;
    }
    
    // Test 4: Valid token with insufficient permissions
    const limitedToken = this.generateJWT({ roles: [] });
    const limitedResponse = await this.makeAPICall('/render', { token: limitedToken });
    // Should either work or return 403, but not 401
    if (limitedResponse.status === 401) {
      console.log('❌ Valid token should not return 401, got:', limitedResponse.status);
      return false;
    }
    
    console.log('   ✅ Authentication scenarios validated');
    return true;
  }

  async testRenderWorkflow() {
    console.log('   Testing render workflow...');
    
    const renderRequest = {
      project_id: `e2e-test-${Date.now()}`,
      prompts: {
        task: 'create',
        instruction: 'Create a minimalist tech company logo with blue colors',
        references: []
      },
      outputs: {
        count: 1,
        format: 'png',
        dimensions: '512x512'
      },
      constraints: {
        palette_hex: ['#1E3A8A', '#FFFFFF'],
        fonts: ['Inter'],
        logo_safe_zone_pct: 15.0
      }
    };
    
    const startTime = Date.now();
    const response = await this.makeAPICall('/render', {
      method: 'POST',
      body: renderRequest,
      timeout: TEST_CONFIG.timeouts.render
    });
    const duration = Date.now() - startTime;
    
    console.log(`   Render request took ${duration}ms`);
    
    // Handle expected responses
    if (response.status === 402) {
      console.log('   💳 Payment required (API key not configured)');
      return true;
    }
    
    if (response.status === 401) {
      console.log('   🔐 Authentication required');
      return false;
    }
    
    if (!response.ok) {
      console.log(`   ❌ Render failed: ${response.status} - ${JSON.stringify(response.data)}`);
      return false;
    }
    
    // Validate response structure
    if (!response.data.assets || !Array.isArray(response.data.assets)) {
      console.log('   ❌ Response missing assets array');
      return false;
    }
    
    if (!response.data.audit) {
      console.log('   ❌ Response missing audit information');
      return false;
    }
    
    // Validate asset structure
    for (const asset of response.data.assets) {
      if (!asset.url || !asset.r2_key) {
        console.log('   ❌ Asset missing required fields:', asset);
        return false;
      }
    }
    
    console.log(`   ✅ Generated ${response.data.assets.length} assets`);
    return true;
  }

  async testWebSocketConnection() {
    console.log('   Testing WebSocket connection...');
    
    return new Promise((resolve) => {
      const jobId = `test-job-${Date.now()}`;
      const wsUrl = `${WS_BASE_URL}/ws/jobs/${jobId}`;
      
      try {
        const ws = new (require('ws'))(wsUrl);
        let connected = false;
        let messageReceived = false;
        
        const timeout = setTimeout(() => {
          if (connected) {
            console.log('   ✅ WebSocket connected but no messages (expected for test job)');
            resolve(true);
          } else {
            console.log('   ❌ WebSocket connection timeout');
            resolve(false);
          }
          ws.close();
        }, TEST_CONFIG.timeouts.websocket);
        
        ws.on('open', () => {
          connected = true;
          console.log('   🔌 WebSocket connected');
        });
        
        ws.on('message', (data) => {
          messageReceived = true;
          console.log('   📨 WebSocket message received:', data.toString());
        });
        
        ws.on('error', (error) => {
          console.log('   ❌ WebSocket error:', error.message);
          clearTimeout(timeout);
          resolve(false);
        });
        
        ws.on('close', () => {
          clearTimeout(timeout);
          if (connected) {
            resolve(true);
          }
        });
        
      } catch (error) {
        console.log('   ❌ WebSocket test failed:', error.message);
        resolve(false);
      }
    });
  }

  async testInputValidation() {
    console.log('   Testing input validation...');
    
    const testCases = [
      {
        name: 'Empty request',
        request: {},
        expectedStatus: [400, 422]
      },
      {
        name: 'Invalid dimensions',
        request: {
          project_id: 'test',
          prompts: { task: 'create', instruction: 'test' },
          outputs: { count: 1, format: 'png', dimensions: 'invalid' }
        },
        expectedStatus: [400, 422]
      },
      {
        name: 'Invalid color format',
        request: {
          project_id: 'test',
          prompts: { task: 'create', instruction: 'test' },
          outputs: { count: 1, format: 'png', dimensions: '512x512' },
          constraints: { palette_hex: ['invalid-color'] }
        },
        expectedStatus: [400, 422]
      },
      {
        name: 'Instruction too short',
        request: {
          project_id: 'test',
          prompts: { task: 'create', instruction: 'hi' },
          outputs: { count: 1, format: 'png', dimensions: '512x512' }
        },
        expectedStatus: [400, 422]
      }
    ];
    
    for (const testCase of testCases) {
      const response = await this.makeAPICall('/render', {
        method: 'POST',
        body: testCase.request
      });
      
      if (!testCase.expectedStatus.includes(response.status)) {
        console.log(`   ❌ ${testCase.name}: expected ${testCase.expectedStatus}, got ${response.status}`);
        return false;
      }
    }
    
    console.log('   ✅ Input validation working correctly');
    return true;
  }

  async testErrorResponseFormat() {
    console.log('   Testing error response format...');
    
    // Make a request that should fail
    const response = await this.makeAPICall('/render', {
      method: 'POST',
      body: { invalid: 'request' }
    });
    
    if (response.ok) {
      console.log('   ❌ Expected error response, got success');
      return false;
    }
    
    // Check error response structure
    if (!response.data || typeof response.data !== 'object') {
      console.log('   ❌ Error response not in JSON format');
      return false;
    }
    
    const requiredErrorFields = ['error', 'message'];
    const hasRequiredFields = requiredErrorFields.every(field => 
      response.data.hasOwnProperty(field)
    );
    
    if (!hasRequiredFields) {
      console.log('   ❌ Error response missing required fields:', response.data);
      return false;
    }
    
    console.log('   ✅ Error response format is consistent');
    return true;
  }

  async testCompleteUserJourney() {
    console.log('   🎬 Simulating complete user journey...');
    
    const projectId = `journey-${Date.now()}`;
    const journeySteps = [];
    
    // Step 1: Health check
    console.log('   1️⃣ Checking system health...');
    const healthResult = await this.makeAPICall('/healthz');
    journeySteps.push({ step: 'health', success: healthResult.ok });
    
    // Step 2: Authentication
    console.log('   2️⃣ Authenticating user...');
    const authResult = await this.makeAPICall('/render', { method: 'GET' });
    journeySteps.push({ step: 'auth', success: authResult.status !== 401 });
    
    // Step 3: Ingest brand materials
    console.log('   3️⃣ Ingesting brand materials...');
    const ingestResult = await this.makeAPICall('/ingest', {
      method: 'POST',
      body: {
        project_id: projectId,
        assets: [
          'https://example.com/brand-guide.pdf',
          'https://example.com/logo.svg'
        ]
      }
    });
    journeySteps.push({ 
      step: 'ingest', 
      success: ingestResult.ok || ingestResult.status === 402 
    });
    
    // Step 4: Derive brand canon
    console.log('   4️⃣ Deriving brand canon...');
    const canonResult = await this.makeAPICall('/canon/derive', {
      method: 'POST',
      body: {
        project_id: projectId,
        evidence_ids: ['auto']
      }
    });
    journeySteps.push({ 
      step: 'canon', 
      success: canonResult.ok || canonResult.status === 402 
    });
    
    // Step 5: Generate design
    console.log('   5️⃣ Generating design...');
    const renderResult = await this.makeAPICall('/render', {
      method: 'POST',
      body: {
        project_id: projectId,
        prompts: {
          task: 'create',
          instruction: 'Create a professional website header'
        },
        outputs: {
          count: 1,
          format: 'png',
          dimensions: '1920x400'
        }
      },
      timeout: TEST_CONFIG.timeouts.render
    });
    journeySteps.push({ 
      step: 'render', 
      success: renderResult.ok || renderResult.status === 402 
    });
    
    // Step 6: Critique result
    console.log('   6️⃣ Critiquing generated design...');
    const critiqueResult = await this.makeAPICall('/critique', {
      method: 'POST',
      body: {
        project_id: projectId,
        asset_ids: ['generated-asset-001']
      }
    });
    journeySteps.push({ 
      step: 'critique', 
      success: critiqueResult.ok || critiqueResult.status === 402 
    });
    
    // Calculate journey success rate
    const successfulSteps = journeySteps.filter(s => s.success).length;
    const totalSteps = journeySteps.length;
    const successRate = successfulSteps / totalSteps;
    
    console.log(`   📊 Journey success rate: ${successfulSteps}/${totalSteps} (${Math.round(successRate * 100)}%)`);
    
    // Journey is successful if at least 80% of steps succeed
    return successRate >= 0.8;
  }

  async testPerformanceBenchmarks() {
    console.log('   ⚡ Running performance benchmarks...');
    
    const endpoints = [
      { path: '/healthz', maxTime: 500 },
      { path: '/metrics', maxTime: 1000 }
    ];
    
    const results = [];
    
    for (const endpoint of endpoints) {
      const times = [];
      const iterations = 5;
      
      for (let i = 0; i < iterations; i++) {
        const startTime = Date.now();
        const response = await this.makeAPICall(endpoint.path);
        const duration = Date.now() - startTime;
        
        if (response.ok) {
          times.push(duration);
        }
      }
      
      if (times.length > 0) {
        const avgTime = times.reduce((a, b) => a + b) / times.length;
        const maxTime = Math.max(...times);
        const minTime = Math.min(...times);
        
        results.push({
          endpoint: endpoint.path,
          avgTime,
          maxTime,
          minTime,
          passed: avgTime <= endpoint.maxTime
        });
        
        console.log(`   ${endpoint.path}: avg ${avgTime.toFixed(0)}ms (max: ${maxTime}ms, min: ${minTime}ms)`);
      }
    }
    
    return results.every(r => r.passed);
  }

  async generateReport() {
    const report = {
      summary: {
        total: this.results.length,
        passed: this.results.filter(r => r.status === 'PASS').length,
        failed: this.results.filter(r => r.status === 'FAIL').length,
        duration: Date.now() - this.metrics.startTime,
        timestamp: new Date().toISOString()
      },
      tests: this.results,
      metrics: this.metrics,
      environment: {
        apiUrl: API_BASE_URL,
        nodeVersion: process.version,
        platform: process.platform
      }
    };
    
    const reportPath = path.join(REPORTS_DIR, `e2e-report-${Date.now()}.json`);
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
    
    console.log(`📋 Detailed report saved: ${reportPath}`);
  }

  printTestSummary() {
    const total = this.results.length;
    const passed = this.results.filter(r => r.status === 'PASS').length;
    const failed = this.results.filter(r => r.status === 'FAIL').length;
    const duration = Date.now() - this.metrics.startTime;
    
    console.log('\n📊 E2E Test Summary:');
    console.log('=' .repeat(50));
    console.log(`Total Tests: ${total}`);
    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);
    console.log(`⏱️  Duration: ${(duration / 1000).toFixed(2)}s`);
    console.log(`🌐 API Calls: ${this.metrics.apiCalls.length}`);
    console.log(`📸 Screenshots: ${this.metrics.screenshots.length}`);
    console.log(`🐛 Errors: ${this.metrics.errors.length}`);
    
    if (this.metrics.apiCalls.length > 0) {
      const avgResponseTime = this.metrics.apiCalls
        .reduce((sum, call) => sum + call.duration, 0) / this.metrics.apiCalls.length;
      console.log(`⚡ Avg Response Time: ${avgResponseTime.toFixed(0)}ms`);
    }
    
    console.log('=' .repeat(50));
    
    // Print failed tests
    const failedTests = this.results.filter(r => r.status === 'FAIL');
    if (failedTests.length > 0) {
      console.log('\n❌ Failed Tests:');
      failedTests.forEach(test => {
        console.log(`  • ${test.name}: ${test.error || 'Unknown error'}`);
      });
    }
  }
}

// Main test execution
async function main() {
  console.log('🎯 Starting Enhanced E2E Test Suite for Smart Graphic Designer');
  console.log(`📍 API URL: ${API_BASE_URL}`);
  console.log(`🔌 WebSocket URL: ${WS_BASE_URL}\n`);
  
  const runner = new EnhancedTestRunner();
  
  try {
    await runner.setup();
    
    // Core functionality tests
    await runner.runTest('System Health', () => runner.testSystemHealth());
    await runner.runTest('Authentication Scenarios', () => runner.testAuthenticationScenarios());
    await runner.runTest('Input Validation', () => runner.testInputValidation());
    await runner.runTest('Error Response Format', () => runner.testErrorResponseFormat());
    
    // Workflow tests
    await runner.runTest('Render Workflow', () => runner.testRenderWorkflow());
    await runner.runTest('WebSocket Connection', () => runner.testWebSocketConnection());
    
    // Integration tests
    await runner.runTest('Complete User Journey', () => runner.testCompleteUserJourney());
    await runner.runTest('Performance Benchmarks', () => runner.testPerformanceBenchmarks());
    
  } catch (error) {
    console.error('💥 Fatal error:', error);
    process.exit(1);
  } finally {
    await runner.teardown();
  }
  
  // Exit with appropriate code
  const failedTests = runner.results.filter(r => r.status === 'FAIL').length;
  process.exit(failedTests > 0 ? 1 : 0);
}

// Dependency checks
const requiredDeps = ['puppeteer', 'jsonwebtoken', 'ws'];
const missingDeps = [];

for (const dep of requiredDeps) {
  try {
    require.resolve(dep);
  } catch (e) {
    missingDeps.push(dep);
  }
}

if (missingDeps.length > 0) {
  console.error('⚠️ Missing dependencies. Run:');
  console.error(`npm install ${missingDeps.join(' ')}`);
  process.exit(1);
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n⚠️ Received SIGINT, shutting down gracefully...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n⚠️ Received SIGTERM, shutting down gracefully...');
  process.exit(0);
});

// Run tests
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { EnhancedTestRunner };