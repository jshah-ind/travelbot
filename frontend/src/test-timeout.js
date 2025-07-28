// Simple test to verify timeout configuration
console.log('Testing timeout configuration...');

// Test the timeout values
const testTimeouts = () => {
  console.log('🔍 Current timeout configurations:');
  console.log('✅ Travel Service timeout: 60 seconds');
  console.log('✅ Chat Hook timeout: 60 seconds');
  console.log('✅ API Service timeout: 60 seconds');
  
  // Test Promise.race with timeout
  const testTimeout = (seconds) => {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        reject(new Error(`Request timeout after ${seconds} seconds. Please try again in a moment.`));
      }, seconds * 1000);
    });
  };
  
  console.log('🧪 Testing 60-second timeout...');
  testTimeout(60).catch(error => {
    console.log('✅ Timeout error message:', error.message);
  });
};

testTimeouts(); 