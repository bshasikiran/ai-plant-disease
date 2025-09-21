# utils/disease_detector.py

import os
import logging
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
import numpy as np
import requests
from io import BytesIO
import base64
import google.generativeai as genai
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DiseaseDetector:
    def __init__(self):
        """Initialize the disease detection system"""
        self.providers_initialized = {}
        self.provider_priority = []
        
        # Load API keys
        self.gemini_key = os.getenv('GEMINI_API_KEY', 'AIzaSyByZjcSzMJJKjQkPt3UDiKwbfKFR54Syg8')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        
        # Initialize providers
        self.init_providers()
        
        # Disease database
        self.init_disease_database()
        
        logger.info("🚀 Disease Detector initialized successfully!")

    def init_providers(self):
        """Initialize AI providers"""
        # Initialize Gemini (Primary provider)
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                self.providers_initialized['gemini'] = True
                self.provider_priority.append('gemini')
                logger.info("✅ Gemini AI initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.providers_initialized['gemini'] = False
        
        # Initialize OpenAI (Backup provider)
        if self.openai_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
                self.providers_initialized['openai'] = True
                self.provider_priority.append('openai')
                logger.info("✅ OpenAI initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                self.providers_initialized['openai'] = False

    def init_disease_database(self):
        """Initialize disease database with common plant diseases"""
        self.disease_database = {
            'early_blight': {
                'name': 'Early Blight',
                'pathogen': 'Alternaria solani',
                'symptoms': ['Dark spots with concentric rings', 'Yellow halos around spots', 'Lower leaves affected first'],
                'crops': ['Tomato', 'Potato', 'Eggplant']
            },
            'late_blight': {
                'name': 'Late Blight',
                'pathogen': 'Phytophthora infestans',
                'symptoms': ['Water-soaked spots', 'White fuzzy growth', 'Rapid plant death'],
                'crops': ['Tomato', 'Potato']
            },
            'powdery_mildew': {
                'name': 'Powdery Mildew',
                'pathogen': 'Erysiphe spp.',
                'symptoms': ['White powdery coating', 'Leaf curling', 'Stunted growth'],
                'crops': ['Cucumber', 'Squash', 'Grapes', 'Roses']
            },
            'bacterial_spot': {
                'name': 'Bacterial Spot',
                'pathogen': 'Xanthomonas spp.',
                'symptoms': ['Dark water-soaked spots', 'Yellow halos', 'Leaf drop'],
                'crops': ['Tomato', 'Pepper']
            },
            'leaf_curl': {
                'name': 'Leaf Curl Virus',
                'pathogen': 'Begomovirus',
                'symptoms': ['Upward leaf curling', 'Leaf thickening', 'Yellowing'],
                'crops': ['Tomato', 'Chili', 'Cotton']
            },
            'rust': {
                'name': 'Rust',
                'pathogen': 'Puccinia spp.',
                'symptoms': ['Orange/rust colored pustules', 'Yellowing leaves', 'Premature leaf drop'],
                'crops': ['Wheat', 'Bean', 'Corn']
            },
            'healthy': {
                'name': 'Healthy Plant',
                'pathogen': 'None',
                'symptoms': ['No visible disease symptoms', 'Normal growth', 'Good color'],
                'crops': ['All']
            }
        }

    def validate_plant_image(self, image_path: str) -> Tuple[bool, float]:
        """Simple validation to check if image is likely a plant"""
        try:
            # Open and check image
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Basic checks
            width, height = img.size
            
            # Check minimum size
            if width < 100 or height < 100:
                return False, 0.0
            
            # Check if image has reasonable dimensions
            if width > 10000 or height > 10000:
                return False, 0.0
            
            # Convert to numpy array for color analysis
            img_array = np.array(img)
            
            # Check for green content (plants usually have green)
            green_channel = img_array[:, :, 1]
            red_channel = img_array[:, :, 0]
            blue_channel = img_array[:, :, 2]
            
            # Calculate green dominance
            green_dominance = np.mean(green_channel > red_channel) * np.mean(green_channel > blue_channel)
            
            # If image has significant green content, likely a plant
            if green_dominance > 0.2:
                confidence = min(95, green_dominance * 100)
                return True, confidence
            
            # Check for brown/yellow (dried plants or diseased)
            avg_red = np.mean(red_channel)
            avg_green = np.mean(green_channel)
            avg_blue = np.mean(blue_channel)
            
            # Brown/yellow detection
            if avg_red > avg_blue and avg_green > avg_blue:
                return True, 70.0
            
            # Default: assume it might be a plant with lower confidence
            return True, 60.0
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            # On error, assume it might be a plant
            return True, 50.0

    def detect_with_gemini(self, image_path: str) -> Dict[str, Any]:
        """Detect disease using Gemini AI"""
        try:
            # Open image
            img = Image.open(image_path)
            
            # Prepare prompt
            prompt = """You are an expert plant pathologist. Analyze this plant image and provide:

1. Plant/Crop Type (if identifiable)
2. Disease Name (or "Healthy" if no disease)
3. Confidence Level (0-100)
4. Pathogen Name (if diseased)
5. Key Symptoms observed
6. Severity (Low/Medium/High)

Please respond in this exact format:
CROP: [crop name]
DISEASE: [disease name or Healthy]
CONFIDENCE: [number]
PATHOGEN: [pathogen name or None]
SYMPTOMS: [comma-separated symptoms]
SEVERITY: [Low/Medium/High/None]

Be specific and accurate. If you cannot identify a disease, state "Healthy" or "Unknown"."""

            # Generate content
            response = self.gemini_model.generate_content([prompt, img])
            
            if response and response.text:
                # Parse response
                result = self.parse_gemini_response(response.text)
                result['provider'] = 'Gemini AI'
                return result
            
        except Exception as e:
            logger.error(f"Gemini detection error: {e}")
        
        return None

    def parse_gemini_response(self, text: str) -> Dict[str, Any]:
        """Parse Gemini response into structured format"""
        import re
        
        result = {
            'disease': 'Unknown',
            'confidence': 75,
            'pathogen': '',
            'symptoms': [],
            'severity': 'Unknown',
            'crop': ''
        }
        
        try:
            # Extract information using regex
            lines = text.strip().split('\n')
            
            for line in lines:
                if 'DISEASE:' in line:
                    disease = line.split('DISEASE:')[1].strip()
                    result['disease'] = disease if disease else 'Unknown'
                
                elif 'CONFIDENCE:' in line:
                    conf = re.search(r'\d+', line)
                    if conf:
                        result['confidence'] = min(100, max(0, int(conf.group())))
                
                elif 'PATHOGEN:' in line:
                    pathogen = line.split('PATHOGEN:')[1].strip()
                    result['pathogen'] = pathogen if pathogen and pathogen.lower() != 'none' else ''
                
                elif 'SYMPTOMS:' in line:
                    symptoms = line.split('SYMPTOMS:')[1].strip()
                    result['symptoms'] = [s.strip() for s in symptoms.split(',') if s.strip()]
                
                elif 'SEVERITY:' in line:
                    severity = line.split('SEVERITY:')[1].strip()
                    result['severity'] = severity if severity else 'Unknown'
                
                elif 'CROP:' in line:
                    crop = line.split('CROP:')[1].strip()
                    result['crop'] = crop if crop else ''
            
            # Validate disease name
            if result['disease'].lower() in ['healthy', 'no disease', 'none']:
                result['disease'] = 'Healthy Plant'
                result['confidence'] = 95
                result['severity'] = 'None'
            
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
        
        return result

    def get_fallback_detection(self, image_path: str) -> Dict[str, Any]:
        """Fallback detection based on image analysis"""
        try:
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # Analyze colors
            avg_color = np.mean(img_array, axis=(0, 1))
            
            # Simple heuristic-based detection
            if avg_color[1] > avg_color[0] and avg_color[1] > avg_color[2]:
                # Greenish - likely healthy
                return {
                    'disease': 'Healthy Plant',
                    'confidence': 70,
                    'pathogen': '',
                    'symptoms': ['Good green color', 'No visible spots'],
                    'severity': 'None',
                    'provider': 'Image Analysis'
                }
            elif avg_color[0] > avg_color[1]:
                # Reddish/Brownish - possible disease
                return {
                    'disease': 'Possible Fungal Disease',
                    'confidence': 60,
                    'pathogen': 'Unknown fungus',
                    'symptoms': ['Discoloration', 'Possible spots'],
                    'severity': 'Medium',
                    'provider': 'Image Analysis'
                }
            else:
                # Yellowish
                return {
                    'disease': 'Nutrient Deficiency or Disease',
                    'confidence': 65,
                    'pathogen': '',
                    'symptoms': ['Yellowing', 'Possible chlorosis'],
                    'severity': 'Low',
                    'provider': 'Image Analysis'
                }
                
        except Exception as e:
            logger.error(f"Fallback detection error: {e}")
            
        return {
            'disease': 'Unknown',
            'confidence': 50,
            'pathogen': '',
            'symptoms': [],
            'severity': 'Unknown',
            'provider': 'Default'
        }

    def get_treatment_recommendations(self, disease: str, pathogen: str = '') -> Dict[str, List[str]]:
        """Get treatment recommendations for detected disease"""
        
        # Check if healthy
        if 'healthy' in disease.lower():
            return {
                'organic': [
                    'Continue regular watering schedule',
                    'Apply organic compost monthly',
                    'Monitor for any changes',
                    'Maintain good air circulation'
                ],
                'chemical': [
                    'No chemical treatment needed',
                    'Optional: Apply balanced NPK fertilizer'
                ],
                'prevention': [
                    'Regular inspection for early detection',
                    'Maintain proper plant spacing',
                    'Remove dead leaves promptly',
                    'Use disease-resistant varieties'
                ],
                'immediate_actions': [],
                'ai_generated': True
            }
        
        # Default disease treatment
        treatment = {
            'organic': [],
            'chemical': [],
            'prevention': [],
            'immediate_actions': [],
            'ai_generated': True
        }
        
        # Check for specific diseases
        disease_lower = disease.lower()
        
        if 'blight' in disease_lower:
            treatment['organic'] = [
                'Remove all infected leaves immediately',
                'Apply neem oil spray (5ml/L water)',
                'Use copper-based organic fungicide',
                'Apply baking soda solution (1 tbsp/gallon)'
            ]
            treatment['chemical'] = [
                'Apply Mancozeb or Chlorothalonil fungicide',
                'Use systemic fungicide for severe cases',
                'Rotate fungicides to prevent resistance'
            ]
            treatment['immediate_actions'] = [
                '🚨 Remove infected parts NOW',
                '🔥 Burn or dispose infected material',
                '💧 Avoid overhead watering'
            ]
            
        elif 'mildew' in disease_lower:
            treatment['organic'] = [
                'Spray with milk solution (40% milk, 60% water)',
                'Apply sulfur-based organic fungicide',
                'Use potassium bicarbonate spray',
                'Neem oil application every 7 days'
            ]
            treatment['chemical'] = [
                'Apply trifloxystrobin or myclobutanil',
                'Use preventive fungicide program',
                'Systemic fungicides for severe infection'
            ]
            treatment['immediate_actions'] = [
                '✂️ Prune affected areas',
                '🌬️ Improve air circulation',
                '☀️ Increase sunlight exposure'
            ]
            
        elif 'spot' in disease_lower or 'bacterial' in disease_lower:
            treatment['organic'] = [
                'Copper hydroxide spray',
                'Remove infected plant debris',
                'Apply compost tea weekly',
                'Use bacterial antagonists (Bacillus subtilis)'
            ]
            treatment['chemical'] = [
                'Copper-based bactericides',
                'Streptomycin (where permitted)',
                'Apply protective sprays before rain'
            ]
            treatment['immediate_actions'] = [
                '💧 Stop overhead irrigation',
                '🧹 Sanitize all tools',
                '🗑️ Remove infected plants'
            ]
            
        elif 'virus' in disease_lower or 'curl' in disease_lower:
            treatment['organic'] = [
                'Remove and destroy infected plants',
                'Control insect vectors (whiteflies, aphids)',
                'Use reflective mulches',
                'Apply neem oil for vector control'
            ]
            treatment['chemical'] = [
                'No cure - focus on vector control',
                'Insecticides for whitefly/aphid control',
                'Imidacloprid for systemic protection'
            ]
            treatment['immediate_actions'] = [
                '⚠️ Isolate infected plants',
                '🐛 Control insect vectors immediately',
                '🌱 Plant resistant varieties'
            ]
            
        elif 'rust' in disease_lower:
            treatment['organic'] = [
                'Remove infected leaves promptly',
                'Apply sulfur dust or spray',
                'Use compost tea as foliar spray',
                'Neem oil application'
            ]
            treatment['chemical'] = [
                'Apply propiconazole or tebuconazole',
                'Use preventive fungicide schedule',
                'Rotate with different fungicide groups'
            ]
            treatment['immediate_actions'] = [
                '🍂 Remove fallen leaves',
                '💨 Ensure good air flow',
                '💧 Water at soil level only'
            ]
        else:
            # Generic treatment
            treatment['organic'] = [
                'Remove affected plant parts',
                'Apply neem oil (5ml/L) every 5-7 days',
                'Improve plant nutrition with compost',
                'Use organic mulch to prevent splash'
            ]
            treatment['chemical'] = [
                'Identify specific pathogen for targeted treatment',
                'Apply broad-spectrum fungicide if fungal',
                'Consult local agricultural extension'
            ]
            treatment['immediate_actions'] = [
                '📸 Document symptoms',
                '🔍 Monitor daily',
                '👨‍🌾 Consult local expert'
            ]
        
        # Common prevention for all diseases
        treatment['prevention'] = [
            'Use disease-resistant varieties',
            'Practice crop rotation',
            'Maintain proper plant spacing',
            'Ensure good drainage',
            'Regular field sanitation',
            'Monitor weather conditions',
            'Apply preventive organic sprays'
        ]
        
        return treatment

    def detect_disease(self, image_path: str) -> Dict[str, Any]:
        """Main method to detect disease"""
        try:
            # Step 1: Validate image
            is_valid, confidence = self.validate_plant_image(image_path)
            
            if not is_valid or confidence < 30:
                return {
                    'error': 'Invalid image',
                    'disease': 'Not a Plant',
                    'confidence': 0,
                    'suggestions': [
                        'Please upload a clear photo of plant leaves or crops',
                        'Ensure good lighting and focus',
                        'Avoid blurry or non-plant images'
                    ]
                }
            
            # Step 2: Try primary detection with Gemini
            result = None
            
            if self.providers_initialized.get('gemini'):
                result = self.detect_with_gemini(image_path)
            
            # Step 3: If Gemini fails, use fallback
            if not result:
                logger.warning("Primary detection failed, using fallback")
                result = self.get_fallback_detection(image_path)
            
            # Step 4: Add treatment recommendations
            if result and result.get('disease'):
                result['treatment'] = self.get_treatment_recommendations(
                    result['disease'],
                    result.get('pathogen', '')
                )
                
                # Add alternatives if confidence is low
                if result.get('confidence', 0) < 70:
                    result['alternatives'] = [
                        'Consider getting a second opinion',
                        'Take multiple photos from different angles',
                        'Consult with local agricultural expert'
                    ]
            
            # Step 5: Ensure all required fields
            if result:
                result.setdefault('disease', 'Unknown')
                result.setdefault('confidence', 50)
                result.setdefault('provider', 'AgriSage AI')
                result.setdefault('symptoms', [])
                result.setdefault('severity', 'Unknown')
            
            return result or {
                'disease': 'Detection Failed',
                'confidence': 0,
                'error': 'Unable to process image',
                'suggestions': ['Please try again with a different image']
            }
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'disease': 'Error',
                'confidence': 0,
                'error': str(e),
                'suggestions': ['Please try again']
            }

# Create global instance
disease_detector = DiseaseDetector()