const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Set up console logging
  page.on('console', msg => {
    console.log('CONSOLE:', msg.type(), msg.text());
  });
  
  // Navigate to the page
  await page.goto('http://localhost:3000');
  
  // Wait for the page to load
  await page.waitForTimeout(2000);
  
  // Execute a direct API call from the browser console to see what happens
  const apiResponse = await page.evaluate(async () => {
    try {
      // Call the API directly
      const response = await fetch('http://localhost:8081/search?q=税制&limit=5&offset=0');
      const data = await response.json();
      
      // Log the raw response
      console.log('Raw API response:', JSON.stringify(data, null, 2));
      
      // Try to access the apiClient from the window
      if (window.apiClient) {
        console.log('apiClient found on window');
        try {
          const searchResult = await window.apiClient.searchBills('税制', 5);
          console.log('ApiClient search result:', JSON.stringify(searchResult, null, 2));
          return searchResult;
        } catch (error) {
          console.log('ApiClient error:', error.message);
          return { error: error.message };
        }
      } else {
        console.log('apiClient not found on window');
        return { raw: data };
      }
    } catch (error) {
      console.log('Direct API call error:', error.message);
      return { error: error.message };
    }
  });
  
  console.log('API response from browser:', JSON.stringify(apiResponse, null, 2));
  
  await browser.close();
})();