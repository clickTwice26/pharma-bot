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
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
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
            return {
                'error': 'Gemini API key not configured',
                'message': 'Please add GEMINI_API_KEY to your .env file'
            }
        
        try:
            # Load and validate image
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create comprehensive prompt for structured extraction
            prompt = """
            You are a medical prescription parser. Analyze this prescription image carefully and extract ALL information.
            
            IMPORTANT RULES:
            1. Extract EVERY medicine mentioned in the prescription
            2. Look carefully at the prescription table/list for Duration and Timing columns
            3. Duration is usually in Days/Quantity/Duration column (e.g., "1.0", "3.0", "7.0" days, "1 week", "2 weeks")
            4. Timing is in the Day/Quantity/Duration/Time/Comment column (e.g., "1-0-1-0", "after meal", "before meal", "30 mins before meal")
            5. Extract dosage from the medicine name or dosage column (e.g., "500mg", "20mg", "5gm")
            6. Extract frequency from Frequency column (e.g., "2 tablet stat then 0+1+0 for 3 days once everyday", "three times a day")
            7. Pay attention to special instructions in the Comment column
            8. If any field is truly not visible in the image, use null (not "As directed")
            
            Extract the following and return as valid JSON:
            
            {
                "doctor_name": "Doctor's full name with prefix (Dr./Prof.) or null if not visible",
                "prescription_date": "Date in YYYY-MM-DD format or null",
                "patient_name": "Patient's full name or null if not visible",
                "patient_age": "Patient's age or null if not visible",
                "patient_gender": "Patient's gender (Male/Female/Other) or null if not visible",
                "medicines": [
                    {
                        "name": "Complete medicine name (brand or generic)",
                        "dosage": "Exact dosage from prescription (e.g. 500mg, 20mg, 5gm, 1 tablet) - extract from medicine name or dosage column",
                        "frequency": "Exact frequency from prescription (e.g. '2 tablet stat then 0+1+0 for 3 days', 'three times a day', '1-0-1-0') - extract from frequency column",
                        "duration": "Exact duration from prescription (e.g. '1.0', '3.0', '7 days', '2 weeks') - extract from duration/days/qty column. If shown as a number like 1.0 or 3.0, convert to '1 day', '3 days'",
                        "instructions": "Exact instructions from prescription (e.g. 'after meal', 'before meal', '30 mins before meal', 'with water', 'mix with 500ml water') - extract from comment/instruction column",
                        "timing": "Exact timing pattern from prescription (e.g. '1-0-1-0' means morning-afternoon-evening-night, 'after meal', 'before meal')"
                    }
                ]
            }
            
            EXAMPLES of correct extraction:
            - If duration column shows "1.0", extract as "1 day"
            - If duration column shows "3.0", extract as "3 days"  
            - If frequency shows "2 tablet stat then 0+1+0 for 3 days", keep exactly as written
            - If timing shows "1-0-1-0", extract as "morning and evening" (1 in morning, 0 afternoon, 1 evening, 0 night)
            - If instruction shows "after meal", extract as "after meal"
            
            CRITICAL: Return ONLY the JSON object. No explanations, no markdown, no additional text.
            """
            
            # Generate response with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(
                        [prompt, img],
                        generation_config={
                            'temperature': 0.1,  # Lower temperature for more consistent output
                            'top_p': 0.8,
                            'top_k': 40
                        }
                    )
                    
                    # Parse JSON response
                    response_text = response.text.strip()
                    
                    # Clean response text
                    response_text = self._clean_json_response(response_text)
                    
                    parsed_data = json.loads(response_text)
                    
                    # Post-process and validate
                    parsed_data = self._post_process_data(parsed_data)
                    
                    return parsed_data
                    
                except json.JSONDecodeError as e:
                    if attempt == max_retries - 1:
                        return {
                            'error': 'Failed to parse AI response',
                            'details': f'JSON parse error: {str(e)}',
                            'raw_response': response.text[:500] if 'response' in locals() else 'No response'
                        }
                    continue
                    
        except Exception as e:
            return {
                'error': 'Failed to process prescription',
                'details': str(e),
                'message': 'Please ensure the image is clear and readable'
            }
    
    def _clean_json_response(self, text):
        """Clean and extract JSON from AI response"""
        # Remove markdown code blocks
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            parts = text.split('```')
            for part in parts:
                if '{' in part and '}' in part:
                    text = part.strip()
                    break
        
        # Find JSON object boundaries
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end > start:
            text = text[start:end]
        
        return text
    
    def _post_process_data(self, data):
        """Post-process and normalize parsed data"""
        if 'medicines' in data and isinstance(data['medicines'], list):
            for medicine in data['medicines']:
                # Normalize empty values - only replace if truly empty or null
                dosage = medicine.get('dosage', '').strip()
                if not dosage or dosage.lower() in ['null', 'none', 'n/a']:
                    medicine['dosage'] = 'As directed'
                
                frequency = medicine.get('frequency', '').strip()
                if not frequency or frequency.lower() in ['null', 'none', 'n/a']:
                    medicine['frequency'] = 'As directed'
                
                duration = medicine.get('duration', '').strip()
                if not duration or duration.lower() in ['null', 'none', 'n/a']:
                    medicine['duration'] = '7 days'
                
                instructions = medicine.get('instructions', '').strip()
                if not instructions or instructions.lower() in ['null', 'none', 'n/a']:
                    medicine['instructions'] = 'Take as prescribed'
                
                timing = medicine.get('timing', '').strip()
                if not timing or timing.lower() in ['null', 'none', 'n/a', 'as directed']:
                    # Only infer timing if not provided
                    medicine['timing'] = self._infer_timing_from_frequency(medicine.get('frequency', 'As directed'))
        
        return data
    
    def _infer_timing_from_frequency(self, frequency):
        """Infer timing from frequency description"""
        freq_lower = frequency.lower()
        
        if 'once' in freq_lower or 'daily' in freq_lower and 'twice' not in freq_lower:
            return 'morning'
        elif 'twice' in freq_lower:
            return 'morning, evening'
        elif 'three' in freq_lower or '3' in freq_lower:
            return 'morning, afternoon, evening'
        elif 'four' in freq_lower or '4' in freq_lower:
            return 'morning, noon, evening, night'
        
        return 'As directed'
    
    def validate_parsed_data(self, data):
        """Validate that parsed data has required fields"""
        if 'error' in data:
            return False, data.get('message', data['error'])
        
        if 'medicines' not in data or not isinstance(data['medicines'], list):
            return False, "No medicines found in prescription. Please upload a clear image."
        
        if len(data['medicines']) == 0:
            return False, "No medicines could be extracted. Please ensure the prescription is clear and readable."
        
        # Validate each medicine has at least a name
        for idx, med in enumerate(data['medicines']):
            if not med.get('name') or med.get('name', '').lower() in ['null', 'none', '']:
                return False, f"Medicine #{idx + 1}: Name could not be read. Please upload a clearer image."
        
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
