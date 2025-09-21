# utils/translator.py

import logging
from googletrans import Translator
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class EnhancedTranslator:
    def __init__(self):
        self.translator = Translator()
        self.cache = {}
        
        # Language configurations
        self.supported_languages = {
            'en': {'name': 'English', 'native': 'English', 'tts_code': 'en'},
            'te': {'name': 'Telugu', 'native': 'తెలుగు', 'tts_code': 'te'},
            'hi': {'name': 'Hindi', 'native': 'हिंदी', 'tts_code': 'hi'},
            'ta': {'name': 'Tamil', 'native': 'தமிழ்', 'tts_code': 'ta'},
            'kn': {'name': 'Kannada', 'native': 'ಕನ್ನಡ', 'tts_code': 'kn'},
            'ml': {'name': 'Malayalam', 'native': 'മലയാളം', 'tts_code': 'ml'},
            'mr': {'name': 'Marathi', 'native': 'मराठी', 'tts_code': 'mr'},
            'gu': {'name': 'Gujarati', 'native': 'ગુજરાતી', 'tts_code': 'gu'},
            'bn': {'name': 'Bengali', 'native': 'বাংলা', 'tts_code': 'bn'},
            'pa': {'name': 'Punjabi', 'native': 'ਪੰਜਾਬੀ', 'tts_code': 'pa'},
        }
        
        # Agricultural terms dictionary for better translation
        self.agri_terms = {
            'en': {
                'disease': 'disease',
                'healthy': 'healthy',
                'plant': 'plant',
                'crop': 'crop',
                'treatment': 'treatment',
                'organic': 'organic',
                'chemical': 'chemical',
                'prevention': 'prevention',
                'blight': 'blight',
                'mildew': 'mildew',
                'rust': 'rust',
                'spot': 'spot',
                'virus': 'virus',
                'fungal': 'fungal',
                'bacterial': 'bacterial',
                'pest': 'pest',
                'fertilizer': 'fertilizer',
                'irrigation': 'irrigation',
                'harvest': 'harvest',
            },
            'te': {
                'disease': 'వ్యాధి',
                'healthy': 'ఆరోగ్యకరమైన',
                'plant': 'మొక్క',
                'crop': 'పంట',
                'treatment': 'చికిత్స',
                'organic': 'సేంద్రీయ',
                'chemical': 'రసాయన',
                'prevention': 'నివారణ',
                'blight': 'కాటుక',
                'mildew': 'బూజు',
                'rust': 'తుప్పు',
                'spot': 'మచ్చ',
                'virus': 'వైరస్',
                'fungal': 'శిలీంధ్ర',
                'bacterial': 'బ్యాక్టీరియా',
                'pest': 'పురుగు',
                'fertilizer': 'ఎరువు',
                'irrigation': 'నీటిపారుదల',
                'harvest': 'కోత',
            },
            'hi': {
                'disease': 'रोग',
                'healthy': 'स्वस्थ',
                'plant': 'पौधा',
                'crop': 'फसल',
                'treatment': 'उपचार',
                'organic': 'जैविक',
                'chemical': 'रासायनिक',
                'prevention': 'रोकथाम',
                'blight': 'झुलसा',
                'mildew': 'फफूंदी',
                'rust': 'जंग',
                'spot': 'धब्बा',
                'virus': 'वायरस',
                'fungal': 'कवक',
                'bacterial': 'जीवाणु',
                'pest': 'कीट',
                'fertilizer': 'उर्वरक',
                'irrigation': 'सिंचाई',
                'harvest': 'फसल काटना',
            }
        }
    
    def translate_text(self, text: str, target_lang: str, source_lang: str = 'auto') -> str:
        """Translate text to target language"""
        try:
            # Check cache first
            cache_key = f"{text}_{source_lang}_{target_lang}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Don't translate if already in target language
            if source_lang == target_lang:
                return text
            
            # Use agricultural terms dictionary for common terms
            if target_lang in self.agri_terms:
                for eng_term, trans_term in self.agri_terms[target_lang].items():
                    if eng_term.lower() in text.lower():
                        text = text.replace(eng_term, trans_term)
                        text = text.replace(eng_term.capitalize(), trans_term)
                        text = text.replace(eng_term.upper(), trans_term)
            
            # Translate using Google Translate
            result = self.translator.translate(text, dest=target_lang, src=source_lang)
            translated_text = result.text if result else text
            
            # Cache the result
            self.cache[cache_key] = translated_text
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text
    
    def translate_to_telugu(self, text: str) -> str:
        """Specific method for Telugu translation"""
        return self.translate_text(text, 'te', 'en')
    
    def translate_to_hindi(self, text: str) -> str:
        """Specific method for Hindi translation"""
        return self.translate_text(text, 'hi', 'en')
    
    def translate_disease_info(self, disease_info: Dict, target_lang: str) -> Dict:
        """Translate complete disease information"""
        try:
            if target_lang == 'en':
                return disease_info
            
            translated_info = disease_info.copy()
            
            # Translate disease name
            if 'disease' in translated_info:
                translated_info['disease'] = self.translate_text(
                    translated_info['disease'], target_lang
                )
            
            # Translate treatment sections
            if 'treatment' in translated_info:
                treatment = translated_info['treatment']
                
                for section in ['organic', 'chemical', 'prevention', 'immediate_actions']:
                    if section in treatment and isinstance(treatment[section], list):
                        treatment[section] = [
                            self.translate_text(item, target_lang) 
                            for item in treatment[section]
                        ]
                
                if 'special_note' in treatment:
                    treatment['special_note'] = self.translate_text(
                        treatment['special_note'], target_lang
                    )
            
            # Translate symptoms
            if 'symptoms' in translated_info and isinstance(translated_info['symptoms'], list):
                translated_info['symptoms'] = [
                    self.translate_text(symptom, target_lang) 
                    for symptom in translated_info['symptoms']
                ]
            
            return translated_info
            
        except Exception as e:
            logger.error(f"Error translating disease info: {e}")
            return disease_info
    
    def get_audio_text(self, disease_info: Dict, language: str) -> str:
        """Prepare text for audio generation in specific language"""
        try:
            # Translate if needed
            if language != 'en':
                disease_info = self.translate_disease_info(disease_info, language)
            
            # Build audio text
            audio_parts = []
            
            # Disease detection
            if language == 'te':
                audio_parts.append(f"గుర్తించిన వ్యాధి: {disease_info.get('disease', 'తెలియదు')}")
                audio_parts.append(f"నమ్మకం స్థాయి: {disease_info.get('confidence', 0)} శాతం")
            elif language == 'hi':
                audio_parts.append(f"पहचानी गई बीमारी: {disease_info.get('disease', 'अज्ञात')}")
                audio_parts.append(f"विश्वास स्तर: {disease_info.get('confidence', 0)} प्रतिशत")
            else:
                audio_parts.append(f"Disease detected: {disease_info.get('disease', 'Unknown')}")
                audio_parts.append(f"Confidence level: {disease_info.get('confidence', 0)} percent")
            
            # Treatment summary
            if disease_info.get('treatment'):
                treatment = disease_info['treatment']
                
                if language == 'te':
                    if treatment.get('organic'):
                        audio_parts.append(f"సేంద్రీయ చికిత్స: {treatment['organic'][0]}")
                    if treatment.get('chemical'):
                        audio_parts.append(f"రసాయన చికిత్స: {treatment['chemical'][0]}")
                    if treatment.get('prevention'):
                        audio_parts.append(f"నివారణ: {treatment['prevention'][0]}")
                        
                elif language == 'hi':
                    if treatment.get('organic'):
                        audio_parts.append(f"जैविक उपचार: {treatment['organic'][0]}")
                    if treatment.get('chemical'):
                        audio_parts.append(f"रासायनिक उपचार: {treatment['chemical'][0]}")
                    if treatment.get('prevention'):
                        audio_parts.append(f"रोकथाम: {treatment['prevention'][0]}")
                        
                else:
                    if treatment.get('organic'):
                        audio_parts.append(f"Organic treatment: {treatment['organic'][0]}")
                    if treatment.get('chemical'):
                        audio_parts.append(f"Chemical treatment: {treatment['chemical'][0]}")
                    if treatment.get('prevention'):
                        audio_parts.append(f"Prevention: {treatment['prevention'][0]}")
            
            return ". ".join(audio_parts)
            
        except Exception as e:
            logger.error(f"Error preparing audio text: {e}")
            return "Error generating audio text"

# Create instance
translator = EnhancedTranslator()

# Keep backward compatibility
class Translator:
    def translate_to_telugu(self, text):
        return translator.translate_to_telugu(text)
    
    def translate_to_hindi(self, text):
        return translator.translate_to_hindi(text)