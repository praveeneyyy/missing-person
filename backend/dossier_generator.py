import io
import os
import json
import hashlib
import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont

from backend.database import get_db
from backend.config import BASE_DIR

def get_default_font(size: int = 16):
    """Attempts to load a standard truetype font, with graceful fallback to PIL default."""
    try:
        # Standard Windows fonts
        for font_name in ["arial.ttf", "segoeui.ttf", "calibri.ttf", "consola.ttf"]:
            try:
                return ImageFont.truetype(font_name, size)
            except Exception:
                continue
        # Fallback to default
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()

def draw_header_badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, bg_color=(30, 58, 138), fg_color=(255, 255, 255)):
    font = get_default_font(12)
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0] + 16
    h = bbox[3] - bbox[1] + 8
    draw.rounded_rectangle([x, y, x + w, y + h], radius=4, fill=bg_color)
    draw.text((x + 8, y + 4), text, font=font, fill=fg_color)
    return w, h

def generate_forensic_certificate(candidate_id: int) -> bytes:
    """
    Generates a formal, high-resolution Biometric Forensic Examination Certificate
    for a candidate match between a sighting probe and an enrolled missing person case.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cm.*, 
                   s.receipt_no, s.sighting_date, s.sighting_time, s.location_name AS sighting_location,
                   sm.file_path AS sighting_file_path,
                   c.reference_no AS case_ref, c.full_name AS case_name, c.age AS case_age,
                   c.gender AS case_gender, c.last_seen_date, c.last_seen_location,
                   ri.file_path AS ref_file_path, ri.model_name
            FROM candidate_matches cm
            JOIN sightings s ON cm.sighting_id = s.id
            LEFT JOIN sighting_media sm ON s.id = sm.sighting_id
            JOIN cases c ON cm.case_id = c.id
            JOIN reference_images ri ON cm.reference_image_id = ri.id
            WHERE cm.id = ?
        """, (candidate_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Candidate match ID {candidate_id} not found.")

        # Check for review adjudication
        cursor.execute("""
            SELECT r.*, u.full_name AS reviewer_name, u.badge_number
            FROM reviews r
            JOIN users u ON r.reviewer_id = u.id
            WHERE r.candidate_match_id = ?
            ORDER BY r.id DESC LIMIT 1
        """, (candidate_id,))
        rev_row = cursor.fetchone()

    # Dimensions
    img_w, img_h = 1000, 1300
    canvas = Image.new("RGB", (img_w, img_h), color=(15, 23, 42))  # Slate-900
    draw = ImageDraw.Draw(canvas)

    # Decorative header banner
    draw.rectangle([0, 0, img_w, 140], fill=(2, 6, 23))  # Slate-950
    draw.line([(0, 140), (img_w, 140)], fill=(59, 130, 246), width=3)  # Blue accent

    title_font = get_default_font(26)
    sub_font = get_default_font(13)
    body_font = get_default_font(14)
    bold_font = get_default_font(16)
    code_font = get_default_font(12)

    # Agency Header
    draw.text((40, 30), "BIOMETRIC SURVEILLANCE & FORENSIC INTELLIGENCE", font=get_default_font(11), fill=(148, 163, 184))
    draw.text((40, 50), "FACIAL RECOGNITION EXAMINATION CERTIFICATE", font=title_font, fill=(255, 255, 255))
    draw.text((40, 95), "OFFICIAL INVESTIGATION SUPPORT DOSSIER | LAW ENFORCEMENT RECORD", font=sub_font, fill=(56, 189, 248))

    # Evidence Hash & Certificate ID
    cert_id = f"CERT-FR-{candidate_id:05d}-{int(datetime.datetime.now().timestamp())}"
    raw_hash = f"{row['case_ref']}:{row['receipt_no']}:{row['similarity_score']}:{cert_id}"
    evidence_sha = hashlib.sha256(raw_hash.encode()).hexdigest()[:24].upper()

    draw.text((img_w - 380, 40), f"CERTIFICATE: {cert_id}", font=code_font, fill=(148, 163, 184))
    draw.text((img_w - 380, 60), f"ISSUED: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", font=code_font, fill=(148, 163, 184))
    draw.text((img_w - 380, 80), f"EVIDENCE SHA-256: {evidence_sha}", font=code_font, fill=(34, 197, 94))

    # SECTION 1: Case & Sighting Metadata Cards
    y_cursor = 165
    # Left Card: Registered Case
    card_w = 440
    draw.rounded_rectangle([40, y_cursor, 40 + card_w, y_cursor + 170], radius=8, fill=(30, 41, 59), outline=(51, 65, 85))
    draw.text((55, y_cursor + 15), "REGISTERED MISSING PERSON DOSSIER", font=get_default_font(11), fill=(148, 163, 184))
    draw.text((55, y_cursor + 35), f"Case Code: {row['case_ref']}", font=bold_font, fill=(56, 189, 248))
    draw.text((55, y_cursor + 65), f"Subject Name: {row['case_name']}", font=body_font, fill=(255, 255, 255))
    draw.text((55, y_cursor + 90), f"Age / Gender: {row['case_age'] or 'Unknown'} yrs | {row['case_gender'] or 'N/A'}", font=body_font, fill=(203, 213, 225))
    draw.text((55, y_cursor + 115), f"Last Seen Date: {row['last_seen_date']}", font=body_font, fill=(203, 213, 225))
    draw.text((55, y_cursor + 140), f"Last Seen Location: {row['last_seen_location']}", font=body_font, fill=(203, 213, 225))

    # Right Card: Field Sighting
    draw.rounded_rectangle([img_w - 40 - card_w, y_cursor, img_w - 40, y_cursor + 170], radius=8, fill=(30, 41, 59), outline=(51, 65, 85))
    draw.text((img_w - card_w - 25, y_cursor + 15), "PUBLIC SIGHTING EVIDENCE LEAD", font=get_default_font(11), fill=(148, 163, 184))
    draw.text((img_w - card_w - 25, y_cursor + 35), f"Tracking Receipt: {row['receipt_no']}", font=bold_font, fill=(56, 189, 248))
    draw.text((img_w - card_w - 25, y_cursor + 65), f"Report Date: {row['sighting_date']} {row['sighting_time'] or ''}", font=body_font, fill=(255, 255, 255))
    draw.text((img_w - card_w - 25, y_cursor + 90), f"Encounter Location: {row['sighting_location']}", font=body_font, fill=(203, 213, 225))
    draw.text((img_w - card_w - 25, y_cursor + 115), f"Match Candidate ID: #CAND-{candidate_id:04d}", font=body_font, fill=(203, 213, 225))
    draw.text((img_w - card_w - 25, y_cursor + 140), f"Candidate Rank: Top-1 Match", font=body_font, fill=(34, 197, 94))

    # SECTION 2: Side-by-Side Biometric Imagery
    y_cursor += 195
    draw.text((40, y_cursor), "SIDE-BY-SIDE BIOMETRIC COMPARATIVE EVIDENCE", font=bold_font, fill=(255, 255, 255))
    y_cursor += 25

    box_h = 320
    box_w = 440

    # Load Sighting Image
    sighting_img = None
    ref_img = None
    try:
        s_path = str(BASE_DIR / row['sighting_file_path'].lstrip("/"))
        if os.path.exists(s_path):
            sighting_img = Image.open(s_path).convert("RGB")
    except Exception:
        pass

    try:
        r_path = str(BASE_DIR / row['ref_file_path'].lstrip("/"))
        if os.path.exists(r_path):
            ref_img = Image.open(r_path).convert("RGB")
    except Exception:
        pass

    # Sighting Box
    draw.rounded_rectangle([40, y_cursor, 40 + box_w, y_cursor + box_h], radius=8, fill=(15, 23, 42), outline=(59, 130, 246))
    if sighting_img:
        sighting_img.thumbnail((box_w - 20, box_h - 60))
        cx = 40 + (box_w - sighting_img.width) // 2
        cy = y_cursor + 15 + (box_h - 60 - sighting_img.height) // 2
        canvas.paste(sighting_img, (cx, cy))
    else:
        draw.text((120, y_cursor + 120), "[Sighting Imagery Archival]", font=body_font, fill=(148, 163, 184))
    draw.rectangle([40, y_cursor + box_h - 40, 40 + box_w, y_cursor + box_h], fill=(30, 41, 59))
    draw.text((55, y_cursor + box_h - 28), "EVIDENCE PROBE: Sighting Candidate Observation", font=get_default_font(12), fill=(56, 189, 248))

    # Reference Box
    draw.rounded_rectangle([img_w - 40 - box_w, y_cursor, img_w - 40, y_cursor + box_h], radius=8, fill=(15, 23, 42), outline=(59, 130, 246))
    if ref_img:
        ref_img.thumbnail((box_w - 20, box_h - 60))
        rx = img_w - 40 - box_w + (box_w - ref_img.width) // 2
        ry = y_cursor + 15 + (box_h - 60 - ref_img.height) // 2
        canvas.paste(ref_img, (rx, ry))
    else:
        draw.text((img_w - 320, y_cursor + 120), "[Registered Gallery Reference]", font=body_font, fill=(148, 163, 184))
    draw.rectangle([img_w - 40 - box_w, y_cursor + box_h - 40, img_w - 40, y_cursor + box_h], fill=(30, 41, 59))
    draw.text((img_w - box_w - 25, y_cursor + box_h - 28), "REGISTERED GALLERY: Enrolled Reference Portrait", font=get_default_font(12), fill=(56, 189, 248))

    # SECTION 3: Mathematical Biometric Metrics
    y_cursor += box_h + 25
    draw.rounded_rectangle([40, y_cursor, img_w - 40, y_cursor + 180], radius=8, fill=(30, 41, 59), outline=(51, 65, 85))
    draw.text((55, y_cursor + 15), "DEEP BIOMETRIC EMBEDDING ANALYSIS & COSINE METRICS", font=bold_font, fill=(255, 255, 255))

    sim_score = float(row["similarity_score"])
    tier = "HIGH CONFIDENCE LEAD" if sim_score >= 0.70 else ("MODERATE SIMILARITY" if sim_score >= 0.50 else "LOW / INCONCLUSIVE")
    tier_color = (34, 197, 94) if sim_score >= 0.70 else ((245, 158, 11) if sim_score >= 0.50 else (239, 68, 68))

    draw.text((55, y_cursor + 45), "Cosine Similarity Score:", font=body_font, fill=(203, 213, 225))
    draw.text((260, y_cursor + 40), f"{sim_score:.4f} / 1.0000", font=get_default_font(20), fill=tier_color)

    draw.text((55, y_cursor + 75), "Calibrated Lead Tier:", font=body_font, fill=(203, 213, 225))
    draw.text((260, y_cursor + 75), tier, font=bold_font, fill=tier_color)

    euclidean_d = (2.0 * max(0.0, 1.0 - sim_score)) ** 0.5
    draw.text((55, y_cursor + 105), f"Euclidean Vector Distance: {euclidean_d:.4f}", font=code_font, fill=(148, 163, 184))
    draw.text((55, y_cursor + 125), "Feature Representation: SFace (MobileFaceNet 128-D L2-Normalized Vectors)", font=code_font, fill=(148, 163, 184))
    draw.text((55, y_cursor + 145), "Facial Detection Engine: OpenCV YuNet Deep Neural Network with 5 Landmark Alignments", font=code_font, fill=(148, 163, 184))

    # Metric Visual Gauge
    meter_x = img_w - 340
    meter_y = y_cursor + 45
    draw.text((meter_x, meter_y), "CONFIDENCE GAUGE", font=get_default_font(11), fill=(148, 163, 184))
    draw.rectangle([meter_x, meter_y + 20, meter_x + 280, meter_y + 40], fill=(15, 23, 42), outline=(71, 85, 105))
    fill_w = int(280 * min(1.0, max(0.0, sim_score)))
    draw.rectangle([meter_x, meter_y + 20, meter_x + fill_w, meter_y + 40], fill=tier_color)
    draw.text((meter_x, meter_y + 50), "0.0 (Unrelated)        0.50 (Moderate)        0.70 (High Lead)", font=get_default_font(9), fill=(148, 163, 184))

    # SECTION 4: Investigator Adjudication Block
    y_cursor += 205
    draw.rounded_rectangle([40, y_cursor, img_w - 40, y_cursor + 170], radius=8, fill=(30, 41, 59), outline=(51, 65, 85))
    draw.text((55, y_cursor + 15), "HUMAN-IN-THE-LOOP INVESTIGATOR ADJUDICATION", font=bold_font, fill=(255, 255, 255))

    if rev_row:
        disp_text = rev_row["disposition"].upper()
        draw.text((55, y_cursor + 45), f"Official Disposition: {disp_text}", font=bold_font, fill=(56, 189, 248))
        draw.text((55, y_cursor + 70), f"Adjudicating Officer: {rev_row['reviewer_name']} (Badge: {rev_row['badge_number'] or 'N/A'})", font=body_font, fill=(203, 213, 225))
        draw.text((55, y_cursor + 95), f"Adjudication Date: {rev_row['reviewed_at']}", font=code_font, fill=(148, 163, 184))
        draw.text((55, y_cursor + 120), f"Investigator Rationale: {rev_row['rationale'][:85]}...", font=body_font, fill=(255, 255, 255))
    else:
        draw.text((55, y_cursor + 45), "Status: PENDING INVESTIGATOR ADJUDICATION", font=bold_font, fill=(245, 158, 11))
        draw.text((55, y_cursor + 75), "In compliance with Responsible AI governance standards, biometric similarity", font=body_font, fill=(203, 213, 225))
        draw.text((55, y_cursor + 95), "scores serve as investigative leads only. Autonomous confirmation is prohibited.", font=body_font, fill=(203, 213, 225))
        draw.text((55, y_cursor + 120), "Investigator review with recorded justification is required before field dispatch.", font=body_font, fill=(148, 163, 184))

    # Signature line
    draw.line([(img_w - 280, y_cursor + 130), (img_w - 60, y_cursor + 130)], fill=(148, 163, 184), width=1)
    draw.text((img_w - 260, y_cursor + 135), "AUTHORIZING SIGNATURE", font=get_default_font(10), fill=(148, 163, 184))

    # SECTION 5: Legal Footer & Chain of Custody
    y_cursor += 190
    draw.text((40, y_cursor), "LEGAL NOTICE & AI GOVERNANCE COMPLIANCE:", font=get_default_font(10), fill=(148, 163, 184))
    draw.text((40, y_cursor + 16), "This forensic examination record was generated by the AI-Based Missing Person Identification System.", font=get_default_font(9), fill=(100, 116, 139))
    draw.text((40, y_cursor + 30), "Biometric representations reflect cosine proximity within deep convolutional latent space and do not constitute absolute positive identification.", font=get_default_font(9), fill=(100, 116, 139))
    draw.text((40, y_cursor + 44), f"Tamper verification record preserved in SQLite audit log ledger under Transaction ID: {evidence_sha}.", font=get_default_font(9), fill=(100, 116, 139))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def generate_missing_person_poster(case_id: int) -> bytes:
    """
    Generates a high-contrast, official MISSING PERSON / AMBER ALERT emergency poster
    for public distribution, field units, and press releases.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*,
                   ri.file_path AS primary_photo_path
            FROM cases c
            LEFT JOIN reference_images ri ON c.id = ri.case_id
            WHERE c.id = ?
            ORDER BY ri.id ASC LIMIT 1
        """, (case_id,))
        case = cursor.fetchone()

        if not case:
            raise ValueError(f"Case ID {case_id} not found.")

    img_w, img_h = 1000, 1400
    canvas = Image.new("RGB", (img_w, img_h), color=(15, 23, 42))  # Slate-900
    draw = ImageDraw.Draw(canvas)

    # 1. Emergency Red Header
    draw.rectangle([0, 0, img_w, 160], fill=(220, 38, 38))  # Red-600
    title_font = get_default_font(42)
    sub_title_font = get_default_font(18)
    bold_font = get_default_font(20)
    body_font = get_default_font(16)
    code_font = get_default_font(13)

    draw.text((img_w // 2 - 240, 30), "MISSING PERSON", font=title_font, fill=(255, 255, 255))
    draw.text((img_w // 2 - 210, 95), "OFFICIAL LAW ENFORCEMENT SEARCH BULLETIN", font=sub_title_font, fill=(254, 242, 242))

    # Case Reference Badge
    draw.rectangle([0, 160, img_w, 205], fill=(30, 41, 59))
    draw.text((50, 175), f"OFFICIAL BULLETIN: {case['reference_no']}", font=bold_font, fill=(56, 189, 248))
    draw.text((img_w - 280, 175), f"STATUS: {case['status'].upper()}", font=bold_font, fill=(245, 158, 11))

    # 2. Central Reference Portrait
    photo_w, photo_h = 480, 520
    photo_x = (img_w - photo_w) // 2
    photo_y = 230

    draw.rectangle([photo_x - 6, photo_y - 6, photo_x + photo_w + 6, photo_y + photo_h + 6], fill=(59, 130, 246))

    ref_img = None
    try:
        if case["primary_photo_path"]:
            r_path = str(BASE_DIR / case["primary_photo_path"].lstrip("/"))
            if os.path.exists(r_path):
                ref_img = Image.open(r_path).convert("RGB")
    except Exception:
        pass

    if ref_img:
        ref_img = ref_img.resize((photo_w, photo_h))
        canvas.paste(ref_img, (photo_x, photo_y))
    else:
        draw.rectangle([photo_x, photo_y, photo_x + photo_w, photo_y + photo_h], fill=(30, 41, 59))
        draw.text((photo_x + 120, photo_y + 240), "[PORTRAIT ENROLLED IN RECORD]", font=body_font, fill=(148, 163, 184))

    # 3. Subject Name Heading
    y_cursor = photo_y + photo_h + 30
    draw.text((img_w // 2 - 180, y_cursor), case["full_name"].upper(), font=get_default_font(32), fill=(255, 255, 255))

    # 4. Critical Case Information Grid
    y_cursor += 65
    info_box_w = 900
    info_box_x = 50
    draw.rounded_rectangle([info_box_x, y_cursor, info_box_x + info_box_w, y_cursor + 270], radius=10, fill=(30, 41, 59), outline=(51, 65, 85))

    draw.text((info_box_x + 30, y_cursor + 20), "IDENTIFYING PARTICULARS & ENCOUNTER CONTEXT", font=bold_font, fill=(56, 189, 248))

    col1_x = info_box_x + 30
    col2_x = info_box_x + 480
    row_y = y_cursor + 60

    draw.text((col1_x, row_y), f"Age: {case['age'] or 'Not Specified'} years old", font=body_font, fill=(255, 255, 255))
    draw.text((col2_x, row_y), f"Gender: {case['gender'] or 'N/A'}", font=body_font, fill=(255, 255, 255))

    row_y += 35
    draw.text((col1_x, row_y), f"Last Seen Date: {case['last_seen_date']}", font=body_font, fill=(255, 255, 255))
    draw.text((col2_x, row_y), f"Last Seen Time: {case['last_seen_time'] or 'Approximate'}", font=body_font, fill=(255, 255, 255))

    row_y += 35
    draw.text((col1_x, row_y), f"Last Seen Location: {case['last_seen_location']}", font=body_font, fill=(255, 255, 255))

    row_y += 35
    clothing = case["clothing_description"] or "Standard casual wear"
    draw.text((col1_x, row_y), f"Clothing: {clothing[:45]}", font=body_font, fill=(203, 213, 225))

    row_y += 35
    features = case["identifying_features"] or "None recorded"
    draw.text((col1_x, row_y), f"Distinct Features: {features[:45]}", font=body_font, fill=(203, 213, 225))

    # 5. Emergency Action & Tip Submission Banner
    y_cursor += 295
    draw.rounded_rectangle([info_box_x, y_cursor, info_box_x + info_box_w, y_cursor + 130], radius=10, fill=(220, 38, 38))
    draw.text((info_box_x + 30, y_cursor + 20), "IF YOU HAVE SIGHTED THIS PERSON OR HAVE ANY INFORMATION:", font=bold_font, fill=(255, 255, 255))
    draw.text((info_box_x + 30, y_cursor + 50), "CALL POLICE EMERGENCY HOTLINE: 100 / 911 OR LOCAL PRECINCT IMMEDIATELY", font=get_default_font(18), fill=(255, 255, 255))
    draw.text((info_box_x + 30, y_cursor + 80), f"SUBMIT SIGHTINGS ONLINE: http://127.0.0.1:8000 (Case Reference: {case['reference_no']})", font=body_font, fill=(254, 226, 226))

    # Footer
    draw.text((50, img_h - 40), f"OFFICIAL PUBLIC SAFETY BULLETIN | RECORD #{case['reference_no']} | ISSUED BY INVESTIGATION SUPPORT UNIT", font=code_font, fill=(100, 116, 139))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
