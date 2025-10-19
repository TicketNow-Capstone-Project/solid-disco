import base64
import cv2
import numpy as np
import pytesseract
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Vehicle
from django.contrib.auth.decorators import login_required


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

@login_required
@csrf_exempt
@require_POST
def ocr_process(request):
    try:
        data = json.loads(request.body)
        image_data = data.get('image_data', '')

        if not image_data:
            return JsonResponse({'error': 'No image data provided.'})

        # Decode the base64 image
        format, imgstr = image_data.split(';base64,')
        nparr = np.frombuffer(base64.b64decode(imgstr), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Preprocess the image (enhance text readability)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        # OCR Extraction
        raw_text = pytesseract.image_to_string(thresh)
        print("🧾 OCR RAW TEXT:", raw_text)

        # Clean and normalize
        text = re.sub(r'[^A-Za-z0-9\s:/-]', ' ', raw_text).upper()

        # --- Smart Philippine License Extraction ---
        license_number = re.search(r'([A-Z]{1,2}\d{2,3}-\d{2}-\d{6,7})', text)
        if not license_number:
            license_number = re.search(r'(?:[A-Z]{3}-?\d{6,7})', text)

        name_match = re.search(r'([A-Z]+),\s*([A-Z]+)\s*([A-Z]*)', text)
        birthdate = re.search(r'(\d{4}/\d{2}/\d{2})', text)
        expiry = re.search(r'(\d{4}/\d{2}/\d{2})', text)

        result = {
            'license_number': license_number.group(0) if license_number else '',
            'last_name': name_match.group(1).title() if name_match else '',
            'first_name': name_match.group(2).title() if name_match else '',
            'middle_name': name_match.group(3).title() if name_match and name_match.group(3) else '',
            'birth_date': birthdate.group(0) if birthdate else '',
            'license_expiry': expiry.group(0) if expiry else '',
        }

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)})

@login_required
def vehicle_registration(request):
    return render(request, 'vehicle_registration.html')
