// Main JavaScript for AgriSage

let selectedFile = null;
let currentResults = null;

// DOM Elements
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const preview = document.getElementById('preview');
const previewImage = document.getElementById('previewImage');
const removeImageBtn = document.getElementById('removeImage');
const analyzeBtn = document.getElementById('analyzeBtn');
const resultsSection = document.getElementById('results');
const loading = document.getElementById('loading');
const languageSelect = document.getElementById('language');
const speakBtn = document.getElementById('speakBtn');
const downloadBtn = document.getElementById('downloadBtn');
const newAnalysisBtn = document.getElementById('newAnalysisBtn');
const audioPlayer = document.getElementById('audioPlayer');

// Event Listeners
uploadArea.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileSelect);
removeImageBtn.addEventListener('click', removeImage);
analyzeBtn.addEventListener('click', analyzeImage);
speakBtn.addEventListener('click', speakResults);
downloadBtn.addEventListener('click', downloadReport);
newAnalysisBtn.addEventListener('click', resetAnalysis);

// Drag and Drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

// File Handling
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

function handleFile(file) {
    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp'];
    if (!validTypes.includes(file.type)) {
        alert('Please upload a valid image file (JPG, PNG, GIF, BMP)');
        return;
    }
    
    // Validate file size (16MB)
    if (file.size > 16 * 1024 * 1024) {
        alert('File size must be less than 16MB');
        return;
    }
    
    selectedFile = file;
    displayPreview(file);
    analyzeBtn.disabled = false;
}

function displayPreview(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        preview.style.display = 'block';
        uploadArea.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

function removeImage() {
    selectedFile = null;
    fileInput.value = '';
    preview.style.display = 'none';
    uploadArea.style.display = 'block';
    analyzeBtn.disabled = true;
}

// Analysis
async function analyzeImage() {
    if (!selectedFile) return;
    
    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('language', languageSelect.value);
    
    // Show loading
    loading.style.display = 'block';
    resultsSection.style.display = 'none';
    analyzeBtn.disabled = true;
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentResults = data;
            displayResults(data);
        } else {
            alert(data.error || 'Analysis failed. Please try again.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
    } finally {
        loading.style.display = 'none';
        analyzeBtn.disabled = false;
    }
}

function displayResults(data) {
    // Update disease information
    document.getElementById('diseaseName').textContent = data.disease;
    document.getElementById('confidenceValue').textContent = data.confidence;
    
    // Update confidence bar
    const confidenceBar = document.getElementById('confidenceBar');
    confidenceBar.style.width = `${data.confidence}%`;
    
    // Update treatment information - Display as formatted lists
    if (data.treatment) {
        // Organic Treatment
        const organicDiv = document.getElementById('organicTreatment');
        if (data.treatment.organic && Array.isArray(data.treatment.organic) && data.treatment.organic.length > 0) {
            let organicHTML = '<ul>';
            data.treatment.organic.forEach(item => {
                organicHTML += `<li>${item}</li>`;
            });
            organicHTML += '</ul>';
            organicDiv.innerHTML = organicHTML;
        } else {
            organicDiv.innerHTML = '<p>No organic treatment available</p>';
        }
        
        // Chemical Treatment
        const chemicalDiv = document.getElementById('chemicalTreatment');
        if (data.treatment.chemical && Array.isArray(data.treatment.chemical) && data.treatment.chemical.length > 0) {
            let chemicalHTML = '<ul>';
            data.treatment.chemical.forEach(item => {
                chemicalHTML += `<li>${item}</li>`;
            });
            chemicalHTML += '</ul>';
            chemicalDiv.innerHTML = chemicalHTML;
        } else {
            chemicalDiv.innerHTML = '<p>No chemical treatment available</p>';
        }
        
        // Prevention Methods
        const preventionDiv = document.getElementById('preventionMethods');
        if (data.treatment.prevention && Array.isArray(data.treatment.prevention) && data.treatment.prevention.length > 0) {
            let preventionHTML = '<ul>';
            data.treatment.prevention.forEach(item => {
                preventionHTML += `<li>${item}</li>`;
            });
            preventionHTML += '</ul>';
            preventionDiv.innerHTML = preventionHTML;
        } else {
            preventionDiv.innerHTML = '<p>Standard prevention practices apply</p>';
        }
    }
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Smooth scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Text to Speech
// Text to Speech with multilingual support
async function speakResults() {
    if (!currentResults) return;
    
    const language = languageSelect.value;
    let text = '';
    
    // Prepare text based on language
    if (language === 'te') {
        // Telugu text preparation
        text = `గుర్తించిన వ్యాధి: ${currentResults.disease}. `;
        text += `నమ్మకం స్థాయి: ${currentResults.confidence} శాతం. `;
        
        if (currentResults.treatment) {
            if (currentResults.treatment.organic && currentResults.treatment.organic.length > 0) {
                text += `సేంద్రీయ చికిత్స: ${currentResults.treatment.organic[0]}. `;
            }
            if (currentResults.treatment.chemical && currentResults.treatment.chemical.length > 0) {
                text += `రసాయన చికిత్స: ${currentResults.treatment.chemical[0]}. `;
            }
            if (currentResults.treatment.prevention && currentResults.treatment.prevention.length > 0) {
                text += `నివారణ చర్యలు: ${currentResults.treatment.prevention[0]}. `;
            }
        }
    } else if (language === 'hi') {
        // Hindi text preparation
        text = `पहचानी गई बीमारी: ${currentResults.disease}. `;
        text += `विश्वास स्तर: ${currentResults.confidence} प्रतिशत. `;
        
        if (currentResults.treatment) {
            if (currentResults.treatment.organic && currentResults.treatment.organic.length > 0) {
                text += `जैविक उपचार: ${currentResults.treatment.organic[0]}. `;
            }
            if (currentResults.treatment.chemical && currentResults.treatment.chemical.length > 0) {
                text += `रासायनिक उपचार: ${currentResults.treatment.chemical[0]}. `;
            }
            if (currentResults.treatment.prevention && currentResults.treatment.prevention.length > 0) {
                text += `रोकथाम: ${currentResults.treatment.prevention[0]}. `;
            }
        }
    } else {
        // English text preparation
        text = `Disease detected: ${currentResults.disease}. `;
        text += `Confidence level: ${currentResults.confidence} percent. `;
        
        if (currentResults.treatment) {
            if (currentResults.treatment.organic && currentResults.treatment.organic.length > 0) {
                text += `Organic treatment: ${currentResults.treatment.organic[0]}. `;
            }
            if (currentResults.treatment.chemical && currentResults.treatment.chemical.length > 0) {
                text += `Chemical treatment: ${currentResults.treatment.chemical[0]}. `;
            }
            if (currentResults.treatment.prevention && currentResults.treatment.prevention.length > 0) {
                text += `Prevention: ${currentResults.treatment.prevention[0]}. `;
            }
        }
    }
    
    // Remove special characters that might cause issues
    text = text.replace(/[🌱🔬💊✓•📊🦠⚗️]/g, '');
    
    speakBtn.disabled = true;
    speakBtn.innerHTML = '<span class="btn-icon">🔊</span> Generating Audio...';
    
    try {
        const response = await fetch('/generate_audio', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                language: language
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.audio_url) {
            // Clear any previous audio
            audioPlayer.pause();
            audioPlayer.currentTime = 0;
            
            // Set new audio source and play
            audioPlayer.src = data.audio_url;
            
            // Add event listeners for better control
            audioPlayer.onloadeddata = function() {
                audioPlayer.play().catch(e => {
                    console.error('Audio play error:', e);
                    alert('Audio playback failed. Please try again.');
                });
            };
            
            audioPlayer.onerror = function() {
                console.error('Audio loading error');
                alert('Failed to load audio. Please try again.');
            };
            
            // Show message if fallback was used
            if (data.fallback) {
                console.info(data.message);
            }
        } else {
            alert('Failed to generate audio. Please try again.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to generate audio. Please try again.');
    } finally {
        speakBtn.disabled = false;
        speakBtn.innerHTML = '<span class="btn-icon">🔊</span> Read Aloud';
    }
}

// Download Report
async function downloadReport() {
    if (!currentResults) return;
    
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<span class="btn-icon">📄</span> Generating Report...';
    
    try {
        const response = await fetch('/generate_report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentResults)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'agrisage_report.pdf';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            alert('Failed to generate report');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to generate report');
    } finally {
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = '<span class="btn-icon">📄</span> Download Report';
    }
}

// Reset Analysis
function resetAnalysis() {
    removeImage();
    resultsSection.style.display = 'none';
    currentResults = null;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ===== NEW FEATURES FUNCTIONS =====

// Navigation function
function showSection(section, event) {
    event.preventDefault();
    
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
    
    // Close all widgets
    closeAllWidgets();
}

// Close all widgets helper function
function closeAllWidgets() {
    document.getElementById('weatherWidget').style.display = 'none';
    document.getElementById('communityModal').style.display = 'none';
    document.getElementById('marketWidget').style.display = 'none';
    document.getElementById('tipsWidget').style.display = 'none';
}

// Weather Functions
function showWeatherWidget(event) {
    event.preventDefault();
    closeAllWidgets();
    document.getElementById('weatherWidget').style.display = 'block';
    
    // Update active nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
}

function closeWeatherWidget() {
    document.getElementById('weatherWidget').style.display = 'none';
}

function getLocationWeather() {
    if (navigator.geolocation) {
        const weatherContent = document.getElementById('weatherContent');
        const weatherLocation = document.getElementById('weatherLocation');
        
        // Show loading
        weatherLocation.innerHTML = '<div class="loading-animation"><div class="loading-spinner"></div></div>';
        
        navigator.geolocation.getCurrentPosition(
            position => {
                fetchWeatherData(position.coords.latitude, position.coords.longitude);
            },
            error => {
                weatherLocation.innerHTML = `
                    <div class="error-message">
                        <p>Unable to get your location. Please enable location services.</p>
                        <button onclick="getLocationWeather()" class="btn-location">Try Again</button>
                    </div>
                `;
            }
        );
    } else {
        alert('Geolocation is not supported by your browser.');
    }
}

async function fetchWeatherData(lat, lon) {
    const weatherContent = document.getElementById('weatherContent');
    const weatherLocation = document.getElementById('weatherLocation');
    
    try {
        const response = await fetch('/api/weather', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ lat, lon })
        });
        
        const data = await response.json();
        displayWeatherData(data);
        weatherLocation.style.display = 'none';
        weatherContent.style.display = 'block';
    } catch (error) {
        console.error('Weather fetch error:', error);
        weatherLocation.innerHTML = `
            <div class="error-message">
                <p>Failed to load weather data. Please try again.</p>
                <button onclick="getLocationWeather()" class="btn-location">Retry</button>
            </div>
        `;
    }
}

function displayWeatherData(data) {
    const weatherContent = document.getElementById('weatherContent');
    
    // Create farming advice HTML
    let adviceHTML = '';
    if (data.farming_advice && data.farming_advice.length > 0) {
        adviceHTML = `
            <div class="farming-advice">
                <div class="advice-title">🌾 Farming Recommendations Based on Weather:</div>
                ${data.farming_advice.map(advice => 
                    `<div class="advice-item">${advice}</div>`
                ).join('')}
            </div>
        `;
    }
    
    // Create forecast HTML
    let forecastHTML = '';
    if (data.forecast && data.forecast.length > 0) {
        forecastHTML = `
            <div class="weather-forecast">
                <div class="forecast-title">5-Day Forecast</div>
                <div class="forecast-container">
                    ${data.forecast.map(day => `
                        <div class="forecast-day">
                            <div class="forecast-date">${day.date}</div>
                            <div class="forecast-temp">${day.temp}°C</div>
                            <div class="forecast-desc">${day.description}</div>
                            <div class="detail-label">💧 ${day.humidity}%</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    weatherContent.innerHTML = `
        <div class="current-weather">
            <div class="weather-main">
                <div>
                    <div class="weather-location-name">📍 ${data.location}, ${data.country || ''}</div>
                    <div class="weather-temp">${data.current.temp}°C</div>
                    <div class="weather-desc">${data.current.description}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.2em; margin-bottom: 10px;">Feels like ${data.current.feels_like}°C</div>
                </div>
            </div>
            <div class="weather-details">
                <div class="weather-detail">
                    <div class="detail-label">Humidity</div>
                    <div class="detail-value">💧 ${data.current.humidity}%</div>
                </div>
                <div class="weather-detail">
                    <div class="detail-label">Wind Speed</div>
                    <div class="detail-value">💨 ${data.current.wind_speed} km/h</div>
                </div>
                <div class="weather-detail">
                    <div class="detail-label">Pressure</div>
                    <div class="detail-value">📊 ${data.current.pressure} hPa</div>
                </div>
            </div>
        </div>
        ${adviceHTML}
        ${forecastHTML}
    `;
}

// Community Functions
function showCommunityFeed(event) {
    event.preventDefault();
    closeAllWidgets();
    document.getElementById('communityModal').style.display = 'flex';
    loadCommunityPosts();
    
    // Update active nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
}

function closeCommunityModal() {
    document.getElementById('communityModal').style.display = 'none';
}

async function loadCommunityPosts() {
    const feedContainer = document.getElementById('communityFeed');
    feedContainer.innerHTML = '<div class="loading-animation"><div class="loading-spinner"></div></div>';
    
    try {
        const response = await fetch('/api/community/posts');
        const posts = await response.json();
        
        feedContainer.innerHTML = posts.map(post => `
            <div class="feed-post">
                <div class="post-header">
                    <div>
                        <div class="post-author">${post.author}</div>
                        <div class="post-location">📍 ${post.location} • ${post.timestamp}</div>
                    </div>
                </div>
                <div class="post-content">${post.content}</div>
                ${post.image ? `<img src="${post.image}" class="post-image" alt="Post image" onerror="this.style.display='none'">` : ''}
                <div class="post-tags">
                    ${post.tags.map(tag => `<span class="tag">#${tag}</span>`).join('')}
                </div>
                <div class="post-actions">
                    <div class="post-action" onclick="likePost(${post.id})">
                        👍 ${post.likes} Likes
                    </div>
                    <div class="post-action">
                        💬 ${post.comments} Comments
                    </div>
                    <div class="post-action">
                        🔗 Share
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Community feed error:', error);
        feedContainer.innerHTML = '<div class="error">Failed to load community posts. Please try again.</div>';
    }
}

function likePost(postId) {
    // For now, just show an alert. You can implement actual like functionality later
    alert('Thanks for liking! (Feature coming soon)');
}

// Market Prices Functions
function showMarketPrices(event) {
    event.preventDefault();
    closeAllWidgets();
    document.getElementById('marketWidget').style.display = 'block';
    loadMarketPrices();
    
    // Update active nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
}

function closeMarketWidget() {
    document.getElementById('marketWidget').style.display = 'none';
}

async function loadMarketPrices() {
    const marketContainer = document.getElementById('marketPrices');
    marketContainer.innerHTML = '<div class="loading-animation"><div class="loading-spinner"></div></div>';
    
    try {
        const response = await fetch('/api/market/prices');
        const data = await response.json();
        
        marketContainer.innerHTML = `
            <div class="market-info">
                <div class="market-title">${data.market}</div>
                <div class="market-update">Last Updated: ${data.updated}</div>
            </div>
            ${data.crops.map(item => `
                <div class="price-item">
                    <div class="crop-info">
                        <span class="crop-name">${item.name}</span>
                    </div>
                    <div class="price-info">
                        <div class="crop-price">${item.price}</div>
                        <div class="price-unit">${item.unit}</div>
                        <div class="price-change price-${item.trend}">
                            ${item.trend === 'up' ? '↑' : item.trend === 'down' ? '↓' : '→'} ${item.change}
                        </div>
                    </div>
                </div>
            `).join('')}
        `;
    } catch (error) {
        console.error('Market prices error:', error);
        marketContainer.innerHTML = '<div class="error">Failed to load market prices. Please try again.</div>';
    }
}

// Farming Tips Functions
function showFarmingTips(event) {
    event.preventDefault();
    closeAllWidgets();
    document.getElementById('tipsWidget').style.display = 'block';
    loadFarmingTips();
    
    // Update active nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
}

function closeTipsWidget() {
    document.getElementById('tipsWidget').style.display = 'none';
}

async function loadFarmingTips() {
    const tipsContainer = document.getElementById('farmingTips');
    tipsContainer.innerHTML = '<div class="loading-animation"><div class="loading-spinner"></div></div>';
    
    try {
        const response = await fetch('/api/farming/tips');
        const data = await response.json();
        
        tipsContainer.innerHTML = `
            <div class="tip-of-day">
                <div class="tip-of-day-title">
                    ${data.tip_of_day.icon} Tip of the Day - ${data.tip_of_day.category}
                </div>
                <div class="tip-of-day-content">
                    ${data.tip_of_day.tip}
                </div>
            </div>
            <div class="tips-list">
                ${data.all_tips.map(tip => `
                    <div class="tip-item">
                        <div class="tip-category">
                            ${tip.icon} ${tip.category}
                        </div>
                        <div class="tip-text">${tip.tip}</div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('Farming tips error:', error);
        tipsContainer.innerHTML = '<div class="error">Failed to load farming tips. Please try again.</div>';
    }
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
    }
}

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        // Close all modals
        closeAllWidgets();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('AgriSage initialized with new features!');
});