// Simple Travel Agent Frontend JavaScript
// Use the FastAPI backend on port 8000
const API_BASE = window.location.hostname === 'localhost' && window.location.port === '8000'
    ? 'http://localhost:8000'  // Development mode: frontend on 8000, backend on 8000
    : window.location.origin;  // Production mode: same origin

console.log('Frontend running on:', window.location.origin);
console.log('API_BASE configured as:', API_BASE);

// Authentication state
let currentUser = null;
let authToken = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    // Check for existing auth token
    authToken = localStorage.getItem('authToken');
    if (authToken) {
        // Verify token and get user info
        verifyToken();
    }
    
    // Set up form handlers
    setupFormHandlers();
    
    // Auto-focus search input
    document.getElementById('searchInput').focus();
});

function setupFormHandlers() {
    // Sign in form
    document.getElementById('signInForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        await handleSignIn();
    });
    
    // Sign up form
    document.getElementById('signUpForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        await handleSignUp();
    });
}

async function verifyToken() {
    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            currentUser = await response.json();
            updateAuthUI();
        } else {
            // Token invalid, clear it
            localStorage.removeItem('authToken');
            authToken = null;
        }
    } catch (error) {
        console.error('Token verification failed:', error);
        localStorage.removeItem('authToken');
        authToken = null;
    }
}

function updateAuthUI() {
    const userInfo = document.getElementById('userInfo');
    const authButtons = document.getElementById('authButtons');
    const conversationMemory = document.getElementById('conversationMemory');
    
    if (currentUser) {
        userInfo.textContent = `Welcome, ${currentUser.full_name || currentUser.username}!`;
        authButtons.innerHTML = '<button class="btn btn-secondary" onclick="signOut()">Sign Out</button>';
        conversationMemory.style.display = 'block';
    } else {
        userInfo.textContent = 'Welcome! Sign in to enable conversation memory.';
        authButtons.innerHTML = `
            <button class="btn btn-primary" onclick="showSignInModal()">Sign In</button>
            <button class="btn btn-secondary" onclick="showSignUpModal()">Sign Up</button>
        `;
        conversationMemory.style.display = 'none';
    }
}

async function handleSignIn() {
    const email = document.getElementById('signInEmail').value;
    const password = document.getElementById('signInPassword').value;
    
    try {
        const response = await fetch(`${API_BASE}/auth/signin`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.access_token;
            localStorage.setItem('authToken', authToken);
            currentUser = data.user;
            updateAuthUI();
            closeModal('signInModal');
            showMessage('Successfully signed in!', 'success');
        } else {
            showMessage(data.detail || 'Sign in failed', 'error');
        }
    } catch (error) {
        showMessage('Sign in failed: ' + error.message, 'error');
    }
}

async function handleSignUp() {
    const email = document.getElementById('signUpEmail').value;
    const username = document.getElementById('signUpUsername').value;
    const fullName = document.getElementById('signUpFullName').value;
    const password = document.getElementById('signUpPassword').value;
    
    try {
        const response = await fetch(`${API_BASE}/auth/signup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email,
                username,
                full_name: fullName,
                password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            closeModal('signUpModal');
            showMessage('Account created successfully! Please sign in.', 'success');
            showSignInModal();
        } else {
            showMessage(data.detail || 'Sign up failed', 'error');
        }
    } catch (error) {
        showMessage('Sign up failed: ' + error.message, 'error');
    }
}

function signOut() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    updateAuthUI();
    showMessage('Successfully signed out!', 'success');
}

function showSignInModal() {
    document.getElementById('signInModal').style.display = 'block';
    document.getElementById('signInEmail').focus();
}

function showSignUpModal() {
    document.getElementById('signUpModal').style.display = 'block';
    document.getElementById('signUpEmail').focus();
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function showMessage(message, type) {
    const resultsDiv = document.getElementById('results');
    const messageClass = type === 'success' ? 'success' : 'error';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = messageClass;
    messageDiv.textContent = message;
    
    resultsDiv.insertBefore(messageDiv, resultsDiv.firstChild);
    
    // Remove message after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 5000);
}

function setQuery(query) {
    document.getElementById('searchInput').value = query;
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        searchFlights();
    }
}

async function searchFlights() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        showMessage('Please enter a search query', 'error');
        return;
    }

    const searchBtn = document.getElementById('searchBtn');
    const resultsDiv = document.getElementById('results');

    // Show loading state
    searchBtn.disabled = true;
    searchBtn.textContent = 'Searching...';
    resultsDiv.innerHTML = '<div class="loading">🔍 Searching for flights...</div>';

    try {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Add auth token if available
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }
        
        console.log('Making API request to:', `${API_BASE}/search`);
        console.log('Request payload:', { query: query });

        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                query: query
            })
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Response data:', data);
        displayResults(data);

    } catch (error) {
        console.error('Search error:', error);
        resultsDiv.innerHTML = `
            <div class="error">
                ❌ Error searching flights: ${error.message}
            </div>
        `;
    } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = 'Search Flights';
    }
}

function displayResults(data) {
    const resultsDiv = document.getElementById('results');

    if (data.status === 'error') {
        resultsDiv.innerHTML = `
            <div class="error">
                ❌ ${data.message}
            </div>
        `;
        return;
    }

    if (!data.flights || data.flights.length === 0) {
        resultsDiv.innerHTML = `
            <div class="no-results">
                ✈️ No flights found for your search criteria.
                <br>Try adjusting your dates or destinations.
            </div>
        `;
        return;
    }

    const searchInfo = data.search_info;
    let html = `
        <h3>✅ ${data.message}</h3>
        <p style="color: #666; margin-bottom: 20px;">
            ${searchInfo.origin} → ${searchInfo.destination} on ${searchInfo.departure_date}
        </p>
    `;

    // Show follow-up indicator if applicable
    if (searchInfo.is_follow_up) {
        html += `
            <div class="conversation-memory" style="display: block; margin-bottom: 20px;">
                <h4>💬 Follow-up Query Detected</h4>
                <p>${searchInfo.follow_up_message || 'Using context from your previous search!'}</p>
            </div>
        `;
    }

    data.flights.forEach(flight => {
        html += `
            <div class="flight-card">
                <div class="flight-header">
                    <div class="flight-number">${flight.flight_number} - ${flight.airline}</div>
                    <div class="flight-price">
                        <div style="font-size: 1.2em; color: #667eea;">${flight.price}</div>
                        ${flight.price_eur ? `<div style="font-size: 0.9em; color: #999;">${flight.price_eur}</div>` : ''}
                    </div>
                </div>
                <div class="flight-details">
                    <div class="detail-item">
                        <div class="detail-label">Departure</div>
                        <div class="detail-value">${flight.departure_time} from ${flight.departure_airport}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Arrival</div>
                        <div class="detail-value">${flight.arrival_time} at ${flight.arrival_airport}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Duration</div>
                        <div class="detail-value">${formatDuration(flight.duration)}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Class</div>
                        <div class="detail-value">${flight.cabin_class}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Stops</div>
                        <div class="detail-value">${flight.is_direct ? 'Direct' : flight.stops + ' stop(s)'}</div>
                    </div>
                </div>
            </div>
        `;
    });

    resultsDiv.innerHTML = html;
}

function formatDuration(duration) {
    // Convert PT2H15M to "2h 15m"
    const match = duration.match(/PT(\d+H)?(\d+M)?/);
    if (!match) return duration;
    
    let result = '';
    if (match[1]) result += match[1].replace('H', 'h ');
    if (match[2]) result += match[2].replace('M', 'm');
    
    return result.trim();
}

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}
