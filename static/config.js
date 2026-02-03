// Frontend Configuration
// API URL will be different for local vs production

const config = {
    // API Base URL - Update this after deploying backend to Render
    API_URL: window.location.hostname === 'localhost'
        ? 'http://localhost:8000'  // Local development
        : 'https://YOUR_RENDER_APP.onrender.com',  // Production - REPLACE THIS

    // Application version
    VERSION: '2.0.0',

    // Feature flags
    FEATURES: {
        AI_CHAT: true,
        WHAT_IF_ANALYSIS: true,
        SQL_DEBUG: true
    }
};

// Make config globally available
window.APP_CONFIG = config;
