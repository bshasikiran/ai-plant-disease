import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

class Translator:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
            logger.warning("Gemini API key not found")
    
    def translate_to_telugu(self, text):
        """Translate text to Telugu"""
        try:
            if not self.model:
                # Fallback translations
                translations = {
                    "Apple Scab": "ఆపిల్ స్కాబ్",
                    "Tomato Early Blight": "టమాటో ముందస్తు ముడత",
                    "Potato Late Blight": "బంగాళాదుంప ఆలస్య ముడత",
                    "healthy": "ఆరోగ్యకరమైన",
                    "Apply organic fungicides": "సేంద్రీయ శిలీంద్రనాశకాలను వర్తించండి"
                }
                return translations.get(text, text)
            
            prompt = f"Translate the following agricultural text to Telugu. Keep technical terms simple: {text}"
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return text