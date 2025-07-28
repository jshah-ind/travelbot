# Frontend Timeout Configuration Fix

## 🎯 Problem
The frontend was timing out after 30 seconds, causing users to see "Request timeout after 30 seconds" errors when the backend was working properly but taking longer to respond.

## 🔧 Solution
Increased timeout configurations across all frontend services to 60 seconds to accommodate complex queries and slower API responses.

## 📝 Changes Made

### 1. Travel Service (`src/services/travelService.ts`)
**File:** `travelbot/frontend/src/services/travelService.ts`
**Line:** 107-109

**Before:**
```typescript
setTimeout(() => reject(new Error('Search API timeout')), 120000) // 2 minutes
```

**After:**
```typescript
setTimeout(() => reject(new Error('Request timeout after 60 seconds. Please try again in a moment.')), 60000) // 60 seconds timeout for complex queries
```

### 2. Chat Hook (`src/hooks/useChatWithAuth.ts`)
**File:** `travelbot/frontend/src/hooks/useChatWithAuth.ts`
**Line:** 304-306

**Before:**
```typescript
setTimeout(() => reject(new Error('Request timeout after 30 seconds')), 30000)
```

**After:**
```typescript
setTimeout(() => reject(new Error('Request timeout after 60 seconds. Please try again in a moment.')), 60000)
```

### 3. API Service (`src/services/api.ts`)
**File:** `travelbot/frontend/src/services/api.ts`
**Lines:** 32-42

**Added AbortController with timeout:**
```typescript
// Create AbortController for timeout
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 seconds timeout

const response = await fetch(url, {
  ...config,
  signal: controller.signal
});

clearTimeout(timeoutId);
```

**Added timeout error handling:**
```typescript
// Handle timeout specifically
if (error instanceof Error && error.name === 'AbortError') {
  throw new Error('Request timeout after 60 seconds. Please try again in a moment.');
}
```

## 🎯 Benefits

1. **Increased Timeout**: From 30 seconds to 60 seconds
2. **Consistent Error Messages**: All timeouts now show "60 seconds"
3. **Better User Experience**: More time for complex queries to complete
4. **Robust Error Handling**: Specific handling for timeout errors
5. **AbortController Integration**: Modern fetch timeout implementation

## 🧪 Testing

### Manual Testing
1. Start the frontend application
2. Try a complex query like "flights from Delhi to Mumbai for tomorrow"
3. The system should now wait up to 60 seconds before timing out
4. Error messages should show "60 seconds" instead of "30 seconds"

### Test Script
Run the timeout test:
```bash
cd frontend
node src/test-timeout.js
```

## 📊 Timeout Configuration Summary

| Service | Previous Timeout | New Timeout | Error Message |
|---------|------------------|-------------|---------------|
| Travel Service | 120 seconds | 60 seconds | "Request timeout after 60 seconds" |
| Chat Hook | 30 seconds | 60 seconds | "Request timeout after 60 seconds" |
| API Service | Default | 60 seconds | "Request timeout after 60 seconds" |

## ⚠️ Important Notes

1. **Backend Compatibility**: The backend should handle requests within 60 seconds
2. **User Experience**: Users will wait longer but get more reliable responses
3. **Error Handling**: All timeout errors now have consistent messaging
4. **Performance**: Consider optimizing backend response times for better UX

## 🔄 Next Steps

1. **Monitor Performance**: Watch for actual timeout occurrences
2. **Backend Optimization**: Consider optimizing slow queries
3. **User Feedback**: Collect feedback on the new timeout behavior
4. **Further Adjustments**: If needed, adjust timeout values based on usage patterns

This fix should resolve the timeout issues you were experiencing with the frontend while maintaining good user experience. 