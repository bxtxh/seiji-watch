#!/usr/bin/env node

// Use Node.js 18 built-in fetch
const fetch = globalThis.fetch;

async function testSearchAPI() {
  const baseUrl = "http://localhost:8080";

  try {
    console.log("Testing search API...");

    // Test the search endpoint
    const response = await fetch(`${baseUrl}/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: "税制",
        limit: 5,
      }),
    });

    const data = await response.json();

    console.log("Search Response Status:", response.status);
    console.log(
      "Search Response Headers:",
      response.headers.get("content-type")
    );
    console.log("Search Response Data:", JSON.stringify(data, null, 2));

    if (data.success && data.results && data.results.length > 0) {
      console.log("\n✅ Search API working correctly!");
      console.log(`Found ${data.results.length} results for "税制"`);
      console.log("First result:", data.results[0].title);
      console.log("Source:", data.search_method);
    } else {
      console.log("\n❌ Search API not returning expected results");
    }
  } catch (error) {
    console.error("❌ Search API test failed:", error.message);
  }
}

testSearchAPI();
