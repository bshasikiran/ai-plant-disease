import os
import logging
import json
import time
from typing import Dict, Any, Optional, List
from PIL import Image
import requests
from io import BytesIO
import base64
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DiseaseDetector:
    def __init__(self):
        """Initialize disease detector with AI providers"""
        self.providers_initialized = {}
        self.provider_priority = []

        # Load env keys
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        self.hf_token = os.getenv('HF_TOKEN')

        # Initialize providers
        self.init_gemini()
        self.init_huggingface()

        # Set priority list
        self.set_provider_priority()

        logger.info(f"Providers ready: {self.provider_priority}")

    def init_gemini(self):
        """Initialize Google Gemini client if API key present."""
        if not self.gemini_key:
            self.providers_initialized['gemini'] = False
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            # Keep a reference to the genai module and default model name
            self.genai = genai
            # model name can be adjusted by you; keep as attribute
            self.gemini_model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            self.providers_initialized['gemini'] = True
            logger.info("✅ Gemini initialized")
        except Exception as e:
            logger.warning(f"Gemini init failed: {e}")
            self.providers_initialized['gemini'] = False

    def init_huggingface(self):
        """Initialize HuggingFace inference settings."""
        # list of image classification models to try
        self.hf_models = [
            "zuppif/plantdisease",
            "emre/plant_disease_detection",
            "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
        ]
        self.current_model_idx = 0
        self.update_hf_model()

        if self.hf_token:
            self.hf_headers = {
                "Authorization": f"Bearer {self.hf_token}",
                "Content-Type": "application/octet-stream"
            }
        else:
            self.hf_headers = {"Content-Type": "application/octet-stream"}

        # we still mark huggingface available because we can attempt unauthenticated inference too
        self.providers_initialized['huggingface'] = True

    def update_hf_model(self):
        """Update HF model url based on index."""
        self.current_hf_model = self.hf_models[self.current_model_idx]
        self.hf_api_url = f"https://api-inference.huggingface.co/models/{self.current_hf_model}"

    def set_provider_priority(self):
        """Set provider priority based on initialization success."""
        self.provider_priority = []
        for provider in ['gemini', 'huggingface']:
            if self.providers_initialized.get(provider, False):
                self.provider_priority.append(provider)

        # If none initialized, still keep huggingface as fallback attempt
        if not self.provider_priority:
            self.provider_priority = ['huggingface']

    def clean_text(self, text: str, preserve_newlines: bool = False) -> str:
        """
        Clean text for display. By default collapses whitespace; set preserve_newlines=True
        to keep newline structure for parsing sections.
        """
        if not text:
            return ""

        # Remove KaTeX-like placeholders specifically used earlier
        text = re.sub(r'KATEX_INLINE_OPEN[^)]*KATEX_INLINE_CLOSE', '', text)

        # Remove markdown bold/italic markers but preserve newlines optionally
        text = text.replace('**', '').replace('*', '')

        # Remove markdown headers start
        text = re.sub(r'#{1,6}\s*', '', text)

        if preserve_newlines:
            # Normalize CRLF to LF
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            # Remove duplicate empty lines
            text = re.sub(r'\n\s*\n+', '\n\n', text)
            # Trim spaces on each line
            text = "\n".join([ln.strip() for ln in text.split("\n")])
        else:
            # remove all excess whitespace
            text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def detect_disease(self, image_path: str) -> Dict[str, Any]:
        """Main detection method"""
        logger.info(f"Starting detection for: {image_path}")

        if not os.path.exists(image_path):
            return {
                'disease': 'File Error',
                'confidence': 0,
                'error': 'Image file not found'
            }

        result = None

        # Try providers in priority order
        for provider in self.provider_priority:
            if provider == 'gemini':
                result = self.detect_with_gemini(image_path)
                if result:
                    break
            elif provider == 'huggingface':
                result = self.detect_with_huggingface(image_path)
                if result:
                    break

        # If no detection worked, use fallback
        if not result:
            result = self.get_fallback_detection()

        # Clean disease name
        if result and result.get('disease'):
            result['disease'] = self.clean_text(result['disease'])

        # Generate treatment (or healthy defaults)
        if result and result.get('disease'):
            result['treatment'] = self.generate_ai_treatment(result['disease'], result.get('confidence', 75))

        return result

    def detect_with_gemini(self, image_path: str) -> Optional[Dict]:
        """Detect using Gemini (if configured). Returns dict or None."""
        if not self.providers_initialized.get('gemini'):
            return None

        try:
            # import kept local to avoid import error if not installed
            genai = self.genai

            # Read image bytes
            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            # Build multimodal input
            prompt = (
                "Analyze this plant image and identify any disease.\n\n"
                "IMPORTANT:\n"
                "- If the plant is healthy, reply exactly: Healthy Plant\n"
                "- If diseased, provide ONLY the disease name (one short phrase)\n"
                "- Do not use markdown or extra commentary\n"
                "- Be concise and direct\n\n"
                "What do you see?"
            )

            # The genai API may accept images as 'image' content — below is a tolerant pattern.
            # If your installed google.generativeai client uses a different signature, adapt accordingly.
            # We call generate() with an input list combining text and the image bytes.
            response = genai.generate(
                model=self.gemini_model_name,
                input=[{"role": "user", "content": prompt}, {"type": "image", "image_bytes": image_bytes}],
                temperature=0.1,
                max_output_tokens=150
            )

            # response may have .text or .outputs; unify to string
            text = ""
            if hasattr(response, "text") and response.text:
                text = response.text
            else:
                # Try more complex structure
                try:
                    # Some genai versions: response[0].content[0].text
                    text = str(response)
                except Exception:
                    text = ""

            text = text.strip()
            disease = self.extract_disease_from_text(text)

            confidence = 90 if 'healthy' in disease.lower() else 85

            return {
                'disease': disease,
                'confidence': confidence,
                'provider': 'Gemini AI',
                'raw': text
            }

        except Exception as e:
            logger.error(f"Gemini error: {e}", exc_info=True)
            return None

    def extract_disease_from_text(self, text: str) -> str:
        """Extract clean disease name from AI/text response."""
        if not text:
            return "Unknown Disease"

        # Keep text cleaned but preserve sentence structure
        cleaned = self.clean_text(text, preserve_newlines=False)

        # Detect healthy cases
        healthy_tokens = ['healthy', 'no disease', 'appears healthy', 'looks healthy', 'no sign of disease']
        if any(tok in cleaned.lower() for tok in healthy_tokens):
            return "Healthy Plant"

        # Map common words to canonical names
        diseases = {
            'early blight': 'Early Blight',
            'late blight': 'Late Blight',
            'bacterial spot': 'Bacterial Spot',
            'powdery mildew': 'Powdery Mildew',
            'leaf mold': 'Leaf Mold',
            'leaf spot': 'Leaf Spot',
            'rust': 'Rust Disease',
            'wilt': 'Wilt Disease',
            'root rot': 'Root Rot',
            'mosaic': 'Mosaic Virus',
            'leaf curl': 'Leaf Curl'
        }

        text_lower = cleaned.lower()
        for key, name in diseases.items():
            if key in text_lower:
                return name

        # fallback: first sentence or small phrase
        sentences = re.split(r'[.\n]', text)
        for s in sentences:
            s = s.strip()
            if s:
                # remove punctuation
                s = re.sub(r'[^\w\s-]', '', s)
                if len(s) > 1:
                    return s[:60]
        return "Unknown Disease"

    def generate_ai_treatment(self, disease_name: str, confidence: float) -> Dict:
        """Generate AI-powered treatment. Uses Gemini when available; otherwise falls back."""
        # If healthy, return a small set of recommendations
        if 'healthy' in disease_name.lower():
            return {
                'organic': [
                    'Maintain regular watering schedule and avoid overwatering.',
                    'Apply organic compost monthly to improve soil health.',
                    'Monitor plants regularly for early signs of stress or pests.',
                    'Ensure proper spacing and pruning for good airflow.'
                ],
                'chemical': [
                    'No chemical treatment needed for healthy plants.',
                    'Optional: balanced NPK if nutrient deficiency detected.'
                ],
                'prevention': [
                    'Remove dead leaves and debris regularly.',
                    'Practice crop rotation and use certified seeds.',
                    'Maintain proper drainage and avoid waterlogging.'
                ]
            }

        # Try Gemini to create formatted treatment text
        if self.providers_initialized.get('gemini'):
            try:
                genai = self.genai
                prompt = (
                    f'For the plant disease "{disease_name}", provide treatment recommendations.\n\n'
                    'Format your response EXACTLY like this (no markdown, no asterisks):\n\n'
                    'ORGANIC TREATMENT:\n'
                    '- First organic method with specific measurements\n'
                    '- Second organic method with application details\n'
                    '- Third organic method with frequency\n\n'
                    'CHEMICAL TREATMENT:\n'
                    '- First chemical with exact dosage\n'
                    '- Second chemical with brand names (if appropriate)\n'
                    '- Safety precautions\n\n'
                    'PREVENTION:\n'
                    '- First prevention method\n'
                    '- Second prevention method\n'
                    '- Third prevention method\n\n'
                    'Be specific, practical, and DO NOT use any special formatting or extra commentary.'
                )

                # If your genai version doesn't accept image here, just use text prompt
                response = genai.generate(
                    model=self.gemini_model_name,
                    input=prompt,
                    temperature=0.3,
                    max_output_tokens=500
                )

                # extract text
                text = ""
                if hasattr(response, "text") and response.text:
                    text = response.text
                else:
                    text = str(response)

                # Parse the response (preserve newlines for checking headers)
                treatments = self.parse_treatment_response(text)

                # if any section has content, return it
                if any(treatments.get(k) for k in ['organic', 'chemical', 'prevention']):
                    return treatments

            except Exception as e:
                logger.error(f"Treatment generation (Gemini) error: {e}", exc_info=True)

        # If we reach here, fall back to rule-based treatment
        logger.info("Using fallback treatment (no model generated a result).")
        return self.get_fallback_treatment(disease_name)

    def parse_treatment_response(self, text: str) -> Dict:
        """Parse treatment response while preserving section headers.

        This intentionally preserves new lines so we can detect section lines like:
        ORGANIC TREATMENT:
        - ...
        """
        if not text:
            return self._default_treatments_empty()

        raw = self.clean_text(text, preserve_newlines=True)

        treatments = {
            'organic': [],
            'chemical': [],
            'prevention': []
        }

        current_section = None
        lines = raw.split('\n')

        for ln in lines:
            line = ln.strip()
            if not line:
                continue

            up = line.upper()

            # detect headers (allow small variants)
            if 'ORGANIC TREATMENT' in up or up.startswith('ORGANIC:') or 'ORGANIC' == up:
                current_section = 'organic'
                continue
            if 'CHEMICAL TREATMENT' in up or 'CHEMICAL:' in up or 'CHEMICAL' == up:
                current_section = 'chemical'
                continue
            if 'PREVENTION' in up or up.startswith('PREVENTION:'):
                current_section = 'prevention'
                continue

            # If line starts with dash or bullet, strip bullets
            cleaned_line = re.sub(r'^[\-\u2022\*\s]+', '', line)
            # Remove any leading numbering like "1." or "a)"
            cleaned_line = re.sub(r'^[\d\.\)\s]+', '', cleaned_line)
            cleaned_line = cleaned_line.strip()

            if current_section and cleaned_line:
                # accept reasonable length lines
                if len(cleaned_line) >= 6:
                    treatments[current_section].append(cleaned_line)

                # prevent huge list lengths
                if len(treatments[current_section]) >= 6:
                    # keep up to 6 suggestions per section
                    continue

        # If some sections empty, add sensible defaults (not too verbose)
        if not treatments['organic']:
            treatments['organic'] = ['Apply neem oil spray 5 ml per liter of water; repeat weekly for 3 applications.']
        if not treatments['chemical']:
            treatments['chemical'] = ['Use an appropriate fungicide/insecticide as recommended by local extension; follow label dosage and PPE instructions.']
        if not treatments['prevention']:
            treatments['prevention'] = ['Maintain field hygiene, crop rotation, and proper spacing to reduce disease spread.']

        return treatments

    def _default_treatments_empty(self):
        return {
            'organic': ['Apply neem oil 5 ml per liter of water.'],
            'chemical': ['Consult local agricultural extension for recommended chemicals.'],
            'prevention': ['Maintain sanitation and monitor plants regularly.']
        }

    def get_fallback_treatment(self, disease_name: str) -> Dict:
        """Return rule-based fallback treatment suggestions."""
        disease_lower = disease_name.lower()

        if 'blight' in disease_lower:
            return {
                'organic': [
                    'Remove infected leaves immediately and dispose (do not compost).',
                    'Spray neem oil 5 ml per liter of water every 7 days.',
                    'Apply baking soda spray (1 tbsp per gallon) as adjunct weekly.'
                ],
                'chemical': [
                    'Apply Mancozeb or Chlorothalonil as per label instructions; wear PPE.',
                    'Rotate active ingredients to avoid resistance.'
                ],
                'prevention': [
                    'Ensure 18–24 inches spacing for good airflow.',
                    'Water at the soil level; avoid wet foliage.',
                    'Remove lower leaves that touch soil.'
                ]
            }

        if 'mildew' in disease_lower or 'powdery' in disease_lower:
            return {
                'organic': [
                    'Spray milk solution (1:9 milk:water) weekly.',
                    'Apply sulfur dust early in the morning when dry.'
                ],
                'chemical': [
                    'Apply Potassium bicarbonate or specific fungicide as per local recommendations.'
                ],
                'prevention': [
                    'Avoid excess nitrogen fertilization and increase sunlight exposure.'
                ]
            }

        if 'root rot' in disease_lower or 'rot' in disease_lower:
            return {
                'organic': [
                    'Improve drainage and reduce watering frequency.',
                    'Remove affected plants and avoid replanting in same spot.'
                ],
                'chemical': [
                    'Use soil drench fungicide labeled for root rot if recommended by extension.'
                ],
                'prevention': [
                    'Do not overwater; use raised beds if needed.'
                ]
            }

        # generic fallback
        return {
            'organic': [
                'Remove affected plant parts and destroy them.',
                'Apply neem oil spray 5 ml per liter weekly.',
                'Use compost tea as a foliar spray if available.'
            ],
            'chemical': [
                'Apply appropriate fungicide/insecticide following label directions and PPE.'
            ],
            'prevention': [
                'Maintain crop rotation, sanitation, and monitor crops regularly.'
            ]
        }

    def get_fallback_detection(self) -> Dict[str, Any]:
        """Return a safe fallback detection result if models fail."""
        return {
            'disease': 'Unknown Disease',
            'confidence': 0,
            'provider': 'Fallback',
            'error': 'No provider returned a reliable detection'
        }

    def detect_with_huggingface(self, image_path: str) -> Optional[Dict]:
        """Detect using HuggingFace Inference API. Tries configured models in list."""
        # Try current and next HF models until one returns a usable result
        attempts = 0
        max_attempts = len(self.hf_models)
        start_idx = self.current_model_idx

        while attempts < max_attempts:
            try:
                self.update_hf_model()  # ensure hf_api_url matches current idx
                logger.info(f"Trying HF model: {self.current_hf_model}")

                img = Image.open(image_path)
                img = img.convert('RGB')
                img = img.resize((224, 224), Image.Resampling.LANCZOS)

                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=90)
                image_bytes = buffered.getvalue()

                # Requests to HF Inference
                response = requests.post(self.hf_api_url, headers=self.hf_headers, data=image_bytes, timeout=25)

                if response.status_code == 200:
                    try:
                        results = response.json()
                    except Exception:
                        results = None

                    # Many HF classification models return a list of dicts: [{"label": "...", "score": 0.9}, ...]
                    if isinstance(results, list) and len(results) > 0 and isinstance(results[0], dict):
                        # pick highest score label
                        best = max(results, key=lambda r: r.get('score', 0))
                        label = best.get('label') or best.get('name') or str(best)
                        score = float(best.get('score', 0)) * 100
                        disease = self.extract_disease_from_text(label)
                        return {
                            'disease': disease,
                            'confidence': round(score, 2),
                            'provider': f'HuggingFace:{self.current_hf_model}',
                            'raw': results
                        }

                    # Some models may return {"error": "..."} or textual output
                    if isinstance(results, dict):
                        # If results contains "error", move to next model
                        if 'error' in results:
                            logger.warning(f'HF model {self.current_hf_model} returned error: {results.get("error")}')
                        else:
                            # try to find probable label keys
                            if 'label' in results:
                                disease = self.extract_disease_from_text(results.get('label'))
                                return {
                                    'disease': disease,
                                    'confidence': round(float(results.get('score', 0)) * 100, 2) if results.get('score') else 60,
                                    'provider': f'HuggingFace:{self.current_hf_model}',
                                    'raw': results
                                }

                    # If the model returns plain text
                    text = response.text.strip()
                    if text:
                        disease = self.extract_disease_from_text(text)
                        # use a medium confidence since HF text responses are unpredictable
                        return {
                            'disease': disease,
                            'confidence': 70,
                            'provider': f'HuggingFace:{self.current_hf_model}',
                            'raw': text
                        }

                else:
                    logger.warning(f"HuggingFace model {self.current_hf_model} returned status {response.status_code}: {response.text}")

            except Exception as e:
                logger.error(f"HuggingFace detection error for {self.current_hf_model}: {e}", exc_info=True)

            # rotate to next model and retry
            attempts += 1
            self.current_model_idx = (self.current_model_idx + 1) % len(self.hf_models)
            time.sleep(0.5)

        # If all HF models fail, return None to let the caller choose fallback
        return None
