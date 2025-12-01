"""
Gemini AI Service for Prescription Parsing
Extracts structured medicine data from prescription images
"""
import os
import json
import google.generativeai as genai
from PIL import Image


class GeminiPrescriptionParser:
    """Parse prescription images using Gemini AI"""
    
    def __init__(self, api_key=None):
        """Initialize Gemini AI with API key"""
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
    
    def parse_prescription(self, image_path):
        """
        Parse prescription image and extract medicine information
        
        Returns structured data:
        {
            'doctor_name': str,
            'prescription_date': str,
            'medicines': [
                {
                    'name': str,
                    'dosage': str,
                    'frequency': str,
                    'duration': str,
                    'instructions': str,
                    'timing': str (e.g., 'morning, evening')
                }
            ]
        }
        """
        if not self.model:
            return {'error': 'Gemini API key not configured'}
        
        try:
            # Load image
            img = Image.open(image_path)
            
            # Create detailed prompt for structured extraction
            prompt = """
            Analyze this medical prescription image and extract the following information in JSON format:
            
            1. Doctor's name (if visible)
            2. Prescription date (if visible)
            3. List of all medicines with:
               - Medicine name (generic or brand)
               - Dosage (e.g., "500mg", "2 tablets")
               - Frequency (e.g., "twice daily", "three times a day", "every 8 hours")
               - Duration (e.g., "7 days", "2 weeks", "1 month")
               - Instructions (e.g., "take after meals", "take before bed", "with water")
               - Timing (specific times like "morning, evening" or "8 AM, 2 PM, 8 PM")
            
            Return ONLY valid JSON in this exact format:
            {
                "doctor_name": "Dr. Name or null",
                "prescription_date": "YYYY-MM-DD or null",
                "medicines": [
                    {
                        "name": "Medicine Name",
                        "dosage": "dosage amount",
                        "frequency": "how often",
                        "duration": "how long",
                        "instructions": "special instructions",
                        "timing": "specific times"
                    }
                ]
            }
            
            If you cannot read certain information, use null. Be precise and extract all visible medicine details.
            """
            
            # Generate response
            response = self.model.generate_content([prompt, img])
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif response_text.startswith('```'):
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            parsed_data = json.loads(response_text)
            return parsed_data
            
        except json.JSONDecodeError as e:
            return {
                'error': 'Failed to parse AI response',
                'details': str(e),
                'raw_response': response.text if 'response' in locals() else None
            }
        except Exception as e:
            return {
                'error': 'Failed to process prescription',
                'details': str(e)
            }
    
    def validate_parsed_data(self, data):
        """Validate that parsed data has required fields"""
        if 'error' in data:
            return False, data['error']
        
        if 'medicines' not in data or not isinstance(data['medicines'], list):
            return False, "No medicines found in prescription"
        
        if len(data['medicines']) == 0:
            return False, "Empty medicines list"
        
        # Validate each medicine has required fields
        for med in data['medicines']:
            if not med.get('name'):
                return False, "Medicine name is required"
            if not med.get('dosage'):
                return False, f"Dosage missing for {med.get('name')}"
            if not med.get('frequency'):
                return False, f"Frequency missing for {med.get('name')}"
        
        return True, "Validation successful"
    
    def extract_timing_from_frequency(self, frequency):
        """Convert frequency to specific times (helper method)"""
        frequency_lower = frequency.lower()
        
        timing_map = {
            'once daily': ['09:00'],
            'once a day': ['09:00'],
            'twice daily': ['09:00', '21:00'],
            'twice a day': ['09:00', '21:00'],
            'three times daily': ['08:00', '14:00', '20:00'],
            'three times a day': ['08:00', '14:00', '20:00'],
            'four times daily': ['08:00', '12:00', '16:00', '20:00'],
            'four times a day': ['08:00', '12:00', '16:00', '20:00'],
            'every 6 hours': ['06:00', '12:00', '18:00', '00:00'],
            'every 8 hours': ['08:00', '16:00', '00:00'],
            'every 12 hours': ['08:00', '20:00'],
            'morning': ['09:00'],
            'evening': ['21:00'],
            'night': ['22:00'],
            'bedtime': ['22:00'],
            'before bed': ['22:00']
        }
        
        for pattern, times in timing_map.items():
            if pattern in frequency_lower:
                return times
        
        return ['09:00']  # Default to morning if not specified
