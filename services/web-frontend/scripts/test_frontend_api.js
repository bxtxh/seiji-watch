#!/usr/bin/env node

/**
 * Test frontend API integration
 * Run this script after starting both API Gateway and frontend dev server
 */

const fetch = require('node-fetch');

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

async function testAPIConnection() {
  console.log('Testing Frontend API Integration');
  console.log(`API Base URL: ${API_BASE_URL}`);
  console.log('='.repeat(50));

  // Test 1: Health Check
  console.log('\n1. Testing health endpoint...');
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    const data = await response.json();
    console.log(`✅ Health check passed: ${data.status}`);
  } catch (error) {
    console.log(`❌ Health check failed: ${error.message}`);
  }

  // Test 2: Bills Search
  console.log('\n2. Testing bills search endpoint...');
  try {
    const response = await fetch(`${API_BASE_URL}/api/bills/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: '',
        max_records: 10,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      console.log(`✅ Bills search successful`);
      console.log(`   Found ${data.total_found} bills`);
      if (data.results && data.results.length > 0) {
        console.log(`   First bill: ${data.results[0].fields?.Name || 'N/A'}`);
      }
    } else {
      console.log(`❌ Bills search failed: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    console.log(`❌ Bills search error: ${error.message}`);
  }

  // Test 3: Categories
  console.log('\n3. Testing categories endpoint...');
  try {
    const response = await fetch(`${API_BASE_URL}/api/issues/categories`);
    if (response.ok) {
      const data = await response.json();
      console.log(`✅ Categories fetch successful`);
      console.log(`   Found ${Array.isArray(data) ? data.length : 0} categories`);
    } else {
      console.log(`❌ Categories fetch failed: ${response.status}`);
    }
  } catch (error) {
    console.log(`❌ Categories error: ${error.message}`);
  }

  // Test 4: CORS (simulating browser request)
  console.log('\n4. Testing CORS configuration...');
  try {
    const response = await fetch(`${API_BASE_URL}/api/bills/search`, {
      method: 'OPTIONS',
      headers: {
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
      },
    });

    const corsHeaders = {
      'Access-Control-Allow-Origin': response.headers.get('access-control-allow-origin'),
      'Access-Control-Allow-Methods': response.headers.get('access-control-allow-methods'),
    };

    if (corsHeaders['Access-Control-Allow-Origin']) {
      console.log(`✅ CORS is properly configured`);
      console.log(`   Allowed origin: ${corsHeaders['Access-Control-Allow-Origin']}`);
    } else {
      console.log(`❌ CORS not configured properly`);
    }
  } catch (error) {
    console.log(`❌ CORS test error: ${error.message}`);
  }

  console.log('\n' + '='.repeat(50));
  console.log('Test complete!');
}

// Check if node-fetch is installed
try {
  require.resolve('node-fetch');
  testAPIConnection();
} catch (e) {
  console.log('Please install node-fetch first:');
  console.log('npm install --save-dev node-fetch');
  process.exit(1);
}