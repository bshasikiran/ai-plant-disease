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
    
    // Update treatment information
    if (data.treatment) {
        document.getElementById('organicTreatment').textContent = 
            data.treatment.organic || 'No organic treatment available';
        document.getElementById('chemicalTreatment').textContent = 
            data.treatment.chemical || 'No chemical treatment available';
        document.getElementById('preventionMethods').textContent = 
            data.treatment.prevention || 'No prevention methods available';
    }
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Smooth scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Text to Speech
async function speakResults() {
    if (!currentResults) return;
    
    const text = `
        Disease detected: ${currentResults.disease}.
        Confidence level: ${currentResults.confidence} percent.
        Organic treatment: ${currentResults.treatment?.organic || 'Not available'}.
        Chemical treatment: ${currentResults.treatment?.chemical || 'Not available'}.
        Prevention: ${currentResults.treatment?.prevention || 'Not available'}.
    `;
    
    speakBtn.disabled = true;
    speakBtn.textContent = '🔊 Generating Audio...';
    
    try {
        const response = await fetch('/generate_audio', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                language: languageSelect.value
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.audio_url) {
            audioPlayer.src = data.audio_url;
            audioPlayer.play();
        } else {
            alert('Failed to generate audio');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to generate audio');
    } finally {
        speakBtn.disabled = false;
        speakBtn.textContent = '🔊 Read Aloud';
    }
}

// Download Report
async function downloadReport() {
    if (!currentResults) return;
    
    downloadBtn.disabled = true;
    downloadBtn.textContent = '📄 Generating Report...';
    
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
        downloadBtn.textContent = '📄 Download Report';
    }
}

// Reset Analysis
function resetAnalysis() {
    removeImage();
    resultsSection.style.display = 'none';
    currentResults = null;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('AgriSage initialized');
});