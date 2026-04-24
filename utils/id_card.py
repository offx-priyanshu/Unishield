"""
ID Card Processing Utility — UniShield
===================================
STEP 1 — Registration:
  1. Scan ID Card QR Code  → auto-extract student data
  2. OCR backup            → if QR fails, read text from card image
  3. Face Capture          → encode + store in DB
"""

import re
import json
import base64
import logging
import numpy as np

logger = logging.getLogger(__name__)

# ── Lazy imports ──────────────────────────────────────────────────────────────
try:
    from pyzbar.pyzbar import decode as qr_decode
    from PIL import Image
    import cv2
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    logger.warning("pyzbar/PIL/cv2 not installed — QR scanning disabled.")

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract not installed — OCR backup disabled.")


# =============================================================================
# STEP 1A — QR CODE SCANNER
# =============================================================================

def scan_qr_from_base64(b64_image: str) -> dict:
    """
    Decode QR from base64 image → return parsed student dict or None.
    Tries multiple image preprocessings for best detection.
    """
    if not QR_AVAILABLE:
        return None
    try:
        if ',' in b64_image:
            img_data = base64.b64decode(b64_image.split(',')[-1])
        else:
            img_data = base64.b64decode(b64_image)
            
        np_arr   = np.frombuffer(img_data, np.uint8)
        img_cv   = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        for variant in _preprocess_variants(img_cv):
            pil_img = Image.fromarray(variant)
            decoded = qr_decode(pil_img)
            if decoded:
                raw = decoded[0].data.decode('utf-8').strip()
                logger.info(f"QR decoded: {raw[:100]}")
                return _parse_qr_data(raw)

        logger.info("No QR found in image.")
        return None

    except Exception as e:
        logger.error(f"scan_qr_from_base64 error: {e}")
        return None

def scan_qr_from_file(image_path: str) -> dict:
    if not QR_AVAILABLE: return None
    try:
        img = cv2.imread(image_path)
        for variant in _preprocess_variants(img):
            decoded = qr_decode(Image.fromarray(variant))
            if decoded:
                raw = decoded[0].data.decode('utf-8').strip()
                return _parse_qr_data(raw)
        return None
    except Exception as e:
        logger.error(f"scan_qr_from_file error: {e}")
        return None

# =============================================================================
# STEP 1B — OCR BACKUP (when QR fails)
# =============================================================================

def ocr_from_base64(b64_image: str) -> dict:
    if not OCR_AVAILABLE or not QR_AVAILABLE:
        return None
    try:
        if ',' in b64_image:
            img_data = base64.b64decode(b64_image.split(',')[-1])
        else:
             img_data = base64.b64decode(b64_image)
        np_arr    = np.frombuffer(img_data, np.uint8)
        img_cv    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        gray      = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        denoised  = cv2.fastNlMeansDenoising(gray, h=10)
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        upscaled  = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        raw_text  = pytesseract.image_to_string(
                        Image.fromarray(upscaled),
                        lang='eng',
                        config='--psm 6'
                    )
        logger.info(f"OCR text:\n{raw_text[:200]}")
        return _parse_ocr_text(raw_text)
    except Exception as e:
        logger.error(f"ocr_from_base64 error: {e}")
        return None

# =============================================================================
# MASTER FUNCTION — QR first, OCR fallback
# =============================================================================

def extract_id_card_data(b64_image: str, client_qr_data: str = None) -> dict:
    """
    Master function — tries in order:
      1. client_qr_data  (jsQR already decoded on frontend — fastest)
      2. pyzbar QR scan  (6 preprocessing variants)
      3. pytesseract OCR (fallback)
    Returns success if PRN OR name is found (does not require both).
    """
    def _has_data(d):
        return bool(d and (d.get('prn') or d.get('name') or d.get('student_id')))

    # 1. Client-side jsQR data (already decoded by browser)
    if client_qr_data and client_qr_data.strip():
        parsed = _parse_qr_data(client_qr_data.strip())
        if _has_data(parsed):
            logger.info(f"[ID] Client jsQR success: {str(parsed)[:80]}")
            return {'success': True, 'method': 'qr_client', 'data': parsed}

    # 2. pyzbar server-side QR scan
    if QR_AVAILABLE:
        qr_result = scan_qr_from_base64(b64_image)
        if _has_data(qr_result):
            logger.info(f"[ID] pyzbar QR success: {str(qr_result)[:80]}")
            return {'success': True, 'method': 'qr', 'data': qr_result}
    else:
        logger.warning("[ID] pyzbar not installed — pip install pyzbar")

    # 3. pytesseract OCR fallback
    if OCR_AVAILABLE and QR_AVAILABLE:
        ocr_result = ocr_from_base64(b64_image)
        if _has_data(ocr_result):
            logger.info(f"[ID] OCR success: {str(ocr_result)[:80]}")
            return {'success': True, 'method': 'ocr', 'data': ocr_result}
    else:
        logger.warning("[ID] pytesseract not installed — pip install pytesseract")

    logger.warning("[ID] All extraction methods failed")
    return {
        'success': False,
        'method':  'failed',
        'data':    {},
        'debug': {
            'pyzbar_available':      QR_AVAILABLE,
            'pytesseract_available': OCR_AVAILABLE,
        }
    }


# =============================================================================
# PARSERS
# =============================================================================

def _parse_qr_data(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith('{'):
        try:
            return _normalize_fields(json.loads(raw))
        except json.JSONDecodeError:
            pass
    if ':' in raw:
        data = {}
        for line in raw.splitlines():
            if ':' in line:
                key, _, val = line.partition(':')
                data[key.strip().lower()] = val.strip()
        if data:
            return _normalize_fields(data)
    if '|' in raw:
        parts = [p.strip() for p in raw.split('|')]
        keys  = ['name', 'prn', 'course', 'dob', 'mobile', 'address']
        return _normalize_fields(dict(zip(keys, parts)))
    return _extract_by_regex(raw)

def _parse_ocr_text(text: str) -> dict:
    return _extract_by_regex(text)

def _extract_by_regex(text: str) -> dict:
    data = {}
    m = re.search(r'(?:NAME|STUDENT\s*NAME|FULL\s*NAME)[:\s]+([A-Za-z][A-Za-z\s\.]{2,40})', text, re.IGNORECASE)
    if m: data['name'] = m.group(1).strip()
    m = re.search(r'(?:PRN|ENROLLMENT\s*(?:NO)?|ROLL\s*NO|STUDENT\s*ID|REG(?:ISTRATION)?\s*(?:NO)?)[:\s#.]*([A-Z0-9\-/]{5,20})', text, re.IGNORECASE)
    if m: data['prn'] = m.group(1).strip()
    m = re.search(r'(?:COURSE|BRANCH|DEPARTMENT|PROGRAM(?:ME)?|DEPT)[:\s]+([A-Za-z0-9][A-Za-z0-9\s\.\(\)&\-]{2,80})', text, re.IGNORECASE)
    if m: data['course'] = m.group(1).strip()[:100]
    m = re.search(r'(?:D\.?O\.?B|DATE\s*OF\s*BIRTH|BORN)[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})', text, re.IGNORECASE)
    if m: data['dob'] = m.group(1).strip()
    m = re.search(r'(?:MOB(?:ILE)?|PHONE|CONTACT|PH)[:\s#.]*([6-9]\d{9})', text, re.IGNORECASE)
    if not m: m = re.search(r'\b([6-9]\d{9})\b', text)
    if m: data['mobile'] = m.group(1).strip()
    m = re.search(r'(?:ADDRESS|ADDR|RESIDENCE|ADD)[:\s]+(.{10,150})', text, re.IGNORECASE | re.DOTALL)
    if m: data['address'] = m.group(1).strip().replace('\n', ', ')[:200]
    m = re.search(r'(?:YEAR|SEM(?:ESTER)?)[:\s]+(\d{1}(?:st|nd|rd|th)?)', text, re.IGNORECASE)
    if m: data['year'] = m.group(1).strip()
    m = re.search(r'(?:COLLEGE|UNIVERSITY|INSTITUTE)[:\s]+([A-Za-z\s]{5,80})', text, re.IGNORECASE)
    if m: data['college'] = m.group(1).strip()[:100]
    return _normalize_fields(data)

def _normalize_fields(raw: dict) -> dict:
    alias_map = {
        'student_name': 'name',   'full_name': 'name',   'fullname': 'name',
        'student name': 'name',   'sname': 'name',
        'enrollment':   'prn',    'roll_no':   'prn',    'rollno': 'prn',
        'student_id':   'prn',    'reg_no':    'prn',    'registration': 'prn',
        'enroll':       'prn',    'id':        'prn',    'uid': 'prn',
        'branch':       'course', 'dept':      'course', 'department': 'course',
        'program':      'course', 'programme': 'course',
        'date_of_birth':'dob',    'birth_date':'dob',    'birthdate': 'dob',
        'phone':        'mobile', 'contact':   'mobile', 'mob': 'mobile',
        'mobile_no':    'mobile', 'phone_no':  'mobile', 'ph': 'mobile',
        'addr':         'address','residence': 'address',
        'semester':     'year',   'sem':       'year',
        'university':   'college','institute': 'college',
    }
    normalized = {}
    for key, val in raw.items():
        clean = key.strip().lower().replace(' ', '_')
        std   = alias_map.get(clean, clean)
        if val and str(val).strip():
            normalized[std] = str(val).strip()
    return normalized

def _preprocess_variants(img_cv):
    yield cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    yield cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    up = cv2.resize(img_cv, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    yield cv2.cvtColor(up, cv2.COLOR_BGR2RGB)
    kernel    = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharpened = cv2.filter2D(img_cv, -1, kernel)
    yield cv2.cvtColor(sharpened, cv2.COLOR_BGR2RGB)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    yield cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
    adaptive  = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    yield cv2.cvtColor(adaptive, cv2.COLOR_GRAY2RGB)
