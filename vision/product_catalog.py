"""
KiranaVision — Product Catalog & Visual/Physical Signatures
Maps directly to the 12 seeded SKUs in db/seed.py so any CNN detection
updates the exact database InventoryItem and Transaction records.
"""
from typing import Dict, List, Optional
import numpy as np
import cv2

# The 8 Hero Countertop Products highlighted for quick testing + 4 additional store items
HERO_SKUS: List[str] = [
    "SKU-D001",   # Amul Toned Milk 500ml
    "SKU-D004",   # Amul Butter 100g
    "SKU-D002",   # Amul Paneer 200g
    "SKU-D003",   # Mother Dairy Curd 400g
    "SKU-SN001",  # Maggi 2-Min Noodles 70g
    "SKU-SN002",  # Lay's Classic Salted 26g
    "SKU-S002",   # Tata Salt 1kg
    "SKU-B001",   # Coca Cola 600ml
]

PRODUCT_CATALOG: List[Dict] = [
    {
        "class_idx": 0,
        "sku_id": "SKU-D001",
        "name": "Amul Toned Milk 500ml",
        "short_name": "Amul Milk 500ml",
        "brand": "Amul",
        "category": "dairy",
        "unit_weight_g": 515,
        "weight_tolerance_g": 35,
        "selling_price": 30.0,
        "unit_cost": 22.0,
        "package_type": "poly_pouch",
        "aspect_ratio": 1.30,  # H/W
        "is_hero": True,
        # Primary BGR colors for synthetic template & HSV matching
        "primary_bgr": (245, 245, 245),    # Milk pouch white
        "secondary_bgr": (195, 110, 25),   # Amul Taaza blue band
        "accent_bgr": (35, 35, 215),       # Amul red script
        "hsv_ranges": [
            # White pouch body + Blue band
            {"lower": (95, 70, 70), "upper": (128, 255, 255), "weight": 0.45},
            {"lower": (0, 0, 185), "upper": (180, 45, 255), "weight": 0.40},
            {"lower": (0, 130, 100), "upper": (10, 255, 255), "weight": 0.15},
        ],
        "label_lines": ["AMUL", "TAAZA", "TONED MILK 500ml"],
        "ui_color": "#2563EB",
    },
    {
        "class_idx": 1,
        "sku_id": "SKU-D002",
        "name": "Amul Paneer 200g",
        "short_name": "Amul Paneer 200g",
        "brand": "Amul",
        "category": "dairy",
        "unit_weight_g": 205,
        "weight_tolerance_g": 20,
        "selling_price": 68.0,
        "unit_cost": 55.0,
        "package_type": "thermoform_pack",
        "aspect_ratio": 1.15,
        "is_hero": True,
        "primary_bgr": (235, 245, 250),    # Cream/White
        "secondary_bgr": (45, 180, 240),   # Yellow/Gold header
        "accent_bgr": (30, 135, 45),       # Green veg / paneer accent
        "hsv_ranges": [
            {"lower": (18, 90, 120), "upper": (35, 255, 255), "weight": 0.45},
            {"lower": (0, 0, 180), "upper": (180, 50, 255), "weight": 0.35},
            {"lower": (38, 70, 70), "upper": (82, 255, 255), "weight": 0.20},
        ],
        "label_lines": ["AMUL", "MALAI PANEER", "200g FRESH"],
        "ui_color": "#D97706",
    },
    {
        "class_idx": 2,
        "sku_id": "SKU-D003",
        "name": "Mother Dairy Curd 400g",
        "short_name": "Mother Dairy Curd",
        "brand": "Mother Dairy",
        "category": "dairy",
        "unit_weight_g": 412,
        "weight_tolerance_g": 30,
        "selling_price": 42.0,
        "unit_cost": 35.0,
        "package_type": "cup_pouch",
        "aspect_ratio": 1.20,
        "is_hero": True,
        "primary_bgr": (210, 145, 30),     # Mother Dairy sky/cyan blue
        "secondary_bgr": (245, 248, 250),  # White curd swirl
        "accent_bgr": (170, 85, 15),       # Deep blue logo
        "hsv_ranges": [
            {"lower": (92, 85, 80), "upper": (118, 255, 255), "weight": 0.55},
            {"lower": (0, 0, 185), "upper": (180, 45, 255), "weight": 0.45},
        ],
        "label_lines": ["MOTHER DAIRY", "DAHI / CURD", "400g PACK"],
        "ui_color": "#0284C7",
    },
    {
        "class_idx": 3,
        "sku_id": "SKU-D004",
        "name": "Amul Butter 100g",
        "short_name": "Amul Butter 100g",
        "brand": "Amul",
        "category": "dairy",
        "unit_weight_g": 104,
        "weight_tolerance_g": 12,
        "selling_price": 56.0,
        "unit_cost": 45.0,
        "package_type": "carton_box",
        "aspect_ratio": 0.65,  # Wide rectangular butter box
        "is_hero": True,
        "primary_bgr": (115, 225, 250),    # Butter pastel yellow
        "secondary_bgr": (35, 35, 220),    # Red typography
        "accent_bgr": (200, 110, 30),      # Blue hair/dress of Amul mascot
        "hsv_ranges": [
            {"lower": (20, 75, 140), "upper": (36, 255, 255), "weight": 0.65},
            {"lower": (0, 120, 100), "upper": (12, 255, 255), "weight": 0.35},
        ],
        "label_lines": ["AMUL", "UTTERLY BUTTERLY", "BUTTER 100g"],
        "ui_color": "#EAB308",
    },
    {
        "class_idx": 4,
        "sku_id": "SKU-SN001",
        "name": "Maggi 2-Min Noodles 70g",
        "short_name": "Maggi Noodles 70g",
        "brand": "Nestle",
        "category": "snacks",
        "unit_weight_g": 73,
        "weight_tolerance_g": 10,
        "selling_price": 15.0,
        "unit_cost": 12.0,
        "package_type": "flow_wrap",
        "aspect_ratio": 1.22,
        "is_hero": True,
        "primary_bgr": (15, 215, 252),     # Iconic Maggi bright yellow
        "secondary_bgr": (25, 25, 225),    # Maggi red bubble logo
        "accent_bgr": (30, 120, 30),       # Green masala bowl garnish
        "hsv_ranges": [
            {"lower": (20, 140, 140), "upper": (34, 255, 255), "weight": 0.60},
            {"lower": (0, 140, 110), "upper": (12, 255, 255), "weight": 0.40},
        ],
        "label_lines": ["MAGGI", "2-MINUTE", "MASALA NOODLES 70g"],
        "ui_color": "#F59E0B",
    },
    {
        "class_idx": 5,
        "sku_id": "SKU-SN002",
        "name": "Lay's Classic Salted 26g",
        "short_name": "Lay's Classic 26g",
        "brand": "Lay's",
        "category": "snacks",
        "unit_weight_g": 28,
        "weight_tolerance_g": 8,
        "selling_price": 10.0,
        "unit_cost": 8.0,
        "package_type": "pillow_pouch",
        "aspect_ratio": 1.38,
        "is_hero": True,
        "primary_bgr": (25, 225, 250),     # Lay's classic yellow
        "secondary_bgr": (35, 30, 215),    # Red Lay's banner
        "accent_bgr": (140, 210, 245),     # Potato chip gold
        "hsv_ranges": [
            {"lower": (22, 130, 150), "upper": (35, 255, 255), "weight": 0.65},
            {"lower": (0, 130, 120), "upper": (10, 255, 255), "weight": 0.35},
        ],
        "label_lines": ["LAY'S", "CLASSIC SALTED", "POTATO CHIPS 26g"],
        "ui_color": "#CA8A04",
    },
    {
        "class_idx": 6,
        "sku_id": "SKU-S002",
        "name": "Tata Salt 1kg",
        "short_name": "Tata Salt 1kg",
        "brand": "Tata",
        "category": "staples",
        "unit_weight_g": 1010,
        "weight_tolerance_g": 45,
        "selling_price": 24.0,
        "unit_cost": 18.0,
        "package_type": "brick_pack",
        "aspect_ratio": 1.35,
        "is_hero": True,
        "primary_bgr": (25, 115, 240),     # Tata Salt vibrant orange
        "secondary_bgr": (175, 75, 20),    # Deep Tata blue band
        "accent_bgr": (245, 245, 245),     # White salt wave
        "hsv_ranges": [
            {"lower": (8, 130, 120), "upper": (20, 255, 255), "weight": 0.50},
            {"lower": (100, 100, 60), "upper": (128, 255, 255), "weight": 0.30},
            {"lower": (0, 0, 185), "upper": (180, 45, 255), "weight": 0.20},
        ],
        "label_lines": ["TATA SALT", "VACUUM EVAPORATED", "IODISED 1KG"],
        "ui_color": "#EA580C",
    },
    {
        "class_idx": 7,
        "sku_id": "SKU-B001",
        "name": "Coca Cola 600ml",
        "short_name": "Coca Cola 600ml",
        "brand": "Coca-Cola",
        "category": "beverages",
        "unit_weight_g": 635,
        "weight_tolerance_g": 35,
        "selling_price": 40.0,
        "unit_cost": 28.0,
        "package_type": "pet_bottle",
        "aspect_ratio": 2.35,  # Tall bottle
        "is_hero": True,
        "primary_bgr": (28, 22, 42),       # Dark cola liquid
        "secondary_bgr": (30, 25, 225),    # Coca-Cola red label wrap
        "accent_bgr": (245, 245, 245),     # Spencerian white script
        "hsv_ranges": [
            {"lower": (0, 135, 100), "upper": (10, 255, 255), "weight": 0.45},
            {"lower": (170, 135, 100), "upper": (180, 255, 255), "weight": 0.20},
            {"lower": (0, 0, 10), "upper": (180, 110, 65), "weight": 0.35},
        ],
        "label_lines": ["COCA-COLA", "ORIGINAL TASTE", "600ml PET"],
        "ui_color": "#DC2626",
    },
    {
        "class_idx": 8,
        "sku_id": "SKU-S003",
        "name": "Fortune Sunflower Oil 1L",
        "short_name": "Fortune Oil 1L",
        "brand": "Fortune",
        "category": "staples",
        "unit_weight_g": 925,
        "weight_tolerance_g": 40,
        "selling_price": 155.0,
        "unit_cost": 130.0,
        "package_type": "stand_pouch",
        "aspect_ratio": 1.45,
        "is_hero": False,
        "primary_bgr": (35, 175, 235),     # Golden oil pouch
        "secondary_bgr": (45, 135, 25),    # Fortune green banner
        "accent_bgr": (25, 45, 210),       # Red Fortune badge
        "hsv_ranges": [
            {"lower": (16, 100, 110), "upper": (32, 255, 255), "weight": 0.55},
            {"lower": (38, 80, 60), "upper": (80, 255, 255), "weight": 0.45},
        ],
        "label_lines": ["FORTUNE", "SUNLITE REFINED", "SUNFLOWER OIL 1L"],
        "ui_color": "#16A34A",
    },
    {
        "class_idx": 9,
        "sku_id": "SKU-S001",
        "name": "Aashirvaad Atta 5kg",
        "short_name": "Aashirvaad Atta 5kg",
        "brand": "Aashirvaad",
        "category": "staples",
        "unit_weight_g": 5040,
        "weight_tolerance_g": 120,
        "selling_price": 280.0,
        "unit_cost": 240.0,
        "package_type": "heavy_sack",
        "aspect_ratio": 1.35,
        "is_hero": False,
        "primary_bgr": (25, 65, 215),      # Deep brick red/orange bag
        "secondary_bgr": (40, 185, 245),   # Wheat gold
        "accent_bgr": (25, 110, 45),       # Green crest
        "hsv_ranges": [
            {"lower": (0, 130, 90), "upper": (16, 255, 255), "weight": 0.65},
            {"lower": (18, 110, 120), "upper": (32, 255, 255), "weight": 0.35},
        ],
        "label_lines": ["AASHIRVAAD", "SHUDH CHAKKI ATTA", "5KG PACK"],
        "ui_color": "#B91C1C",
    },
    {
        "class_idx": 10,
        "sku_id": "SKU-PC001",
        "name": "Surf Excel 1kg",
        "short_name": "Surf Excel 1kg",
        "brand": "Surf Excel",
        "category": "personal_care",
        "unit_weight_g": 1015,
        "weight_tolerance_g": 45,
        "selling_price": 220.0,
        "unit_cost": 185.0,
        "package_type": "poly_bag",
        "aspect_ratio": 1.32,
        "is_hero": False,
        "primary_bgr": (185, 85, 20),      # Royal Surf blue
        "secondary_bgr": (245, 245, 245),  # White burst
        "accent_bgr": (95, 35, 235),       # Pink/Orange splat
        "hsv_ranges": [
            {"lower": (100, 110, 70), "upper": (130, 255, 255), "weight": 0.60},
            {"lower": (150, 110, 100), "upper": (179, 255, 255), "weight": 0.20},
            {"lower": (0, 0, 185), "upper": (180, 45, 255), "weight": 0.20},
        ],
        "label_lines": ["SURF EXCEL", "EASY WASH", "DETERGENT 1KG"],
        "ui_color": "#1D4ED8",
    },
    {
        "class_idx": 11,
        "sku_id": "SKU-PC002",
        "name": "Dove Soap 100g",
        "short_name": "Dove Soap 100g",
        "brand": "Dove",
        "category": "personal_care",
        "unit_weight_g": 108,
        "weight_tolerance_g": 12,
        "selling_price": 52.0,
        "unit_cost": 40.0,
        "package_type": "carton_box",
        "aspect_ratio": 0.70,
        "is_hero": False,
        "primary_bgr": (248, 246, 242),    # Pure Dove white box
        "secondary_bgr": (175, 115, 45),   # Navy blue script
        "accent_bgr": (95, 185, 225),      # Gold bird silhouette
        "hsv_ranges": [
            {"lower": (0, 0, 195), "upper": (180, 35, 255), "weight": 0.75},
            {"lower": (95, 60, 60), "upper": (128, 255, 255), "weight": 0.25},
        ],
        "label_lines": ["DOVE", "CREAM BEAUTY", "BATHING BAR 100g"],
        "ui_color": "#64748B",
    },
]

SKU_MAP: Dict[str, Dict] = {item["sku_id"]: item for item in PRODUCT_CATALOG}
CLASS_MAP: Dict[int, Dict] = {item["class_idx"]: item for item in PRODUCT_CATALOG}


def get_product_by_sku(sku_id: str) -> Optional[Dict]:
    return SKU_MAP.get(sku_id)


def get_product_by_class(class_idx: int) -> Optional[Dict]:
    return CLASS_MAP.get(class_idx)


def render_synthetic_packet(sku_id: str, width: int = 240, height: int = 240) -> np.ndarray:
    """
    Generates a deterministic, high-contrast OpenCV synthetic reference packet image
    for a given SKU. Used both for:
      1. Bootstrapping CNN training with realistic color-zone & geometric structure
      2. Rendering reference thumbnails and tabletop test packets
    """
    prod = get_product_by_sku(sku_id)
    if not prod:
        prod = PRODUCT_CATALOG[0]

    canvas = np.full((height, width, 3), (42, 46, 52), dtype=np.uint8)  # Countertop dark slate

    # Compute packet dimensions based on aspect_ratio
    ar = prod.get("aspect_ratio", 1.2)
    if ar >= 1.8:  # Bottle (Coca-Cola)
        pw = int(width * 0.36)
        ph = int(height * 0.82)
    elif ar < 0.85:  # Wide box (Amul Butter / Dove Soap)
        pw = int(width * 0.78)
        ph = int(height * 0.54)
    else:  # Standard pouch / brick pack
        pw = int(width * 0.66)
        ph = int(height * 0.78)

    x1 = (width - pw) // 2
    y1 = (height - ph) // 2
    x2 = x1 + pw
    y2 = y1 + ph

    p_bgr = prod["primary_bgr"]
    s_bgr = prod["secondary_bgr"]
    a_bgr = prod["accent_bgr"]

    # Draw shadow
    cv2.rectangle(canvas, (x1 + 6, y1 + 6), (x2 + 6, y2 + 6), (20, 22, 26), -1)

    # Draw primary packet body
    cv2.rectangle(canvas, (x1, y1), (x2, y2), p_bgr, -1)

    # Package-specific visual bands & geometry
    band_h = int(ph * 0.32)
    cv2.rectangle(canvas, (x1, y1 + int(ph * 0.18)), (x2, y1 + int(ph * 0.18) + band_h), s_bgr, -1)

    # Bottom accent strip
    cv2.rectangle(canvas, (x1, y2 - int(ph * 0.18)), (x2, y2), a_bgr, -1)

    # Central brand crest circle/ellipse
    cx, cy = (x1 + x2) // 2, y1 + int(ph * 0.34)
    cv2.ellipse(canvas, (cx, cy), (int(pw * 0.34), int(band_h * 0.48)), 0, 0, 360, a_bgr, -1)
    cv2.ellipse(canvas, (cx, cy), (int(pw * 0.34), int(band_h * 0.48)), 0, 0, 360, (255, 255, 255), 2)

    # Outer packet border & crimp lines
    cv2.rectangle(canvas, (x1, y1), (x2, y2), (210, 210, 210), 2)

    # Typography lines
    lines = prod.get("label_lines", [prod["brand"].upper(), prod["short_name"].upper()])
    font = cv2.FONT_HERSHEY_SIMPLEX
    if len(lines) > 0:
        cv2.putText(
            canvas, lines[0][:12],
            (x1 + 12, cy + 6),
            font, 0.56, (255, 255, 255), 2, cv2.LINE_AA
        )
    if len(lines) > 1:
        cv2.putText(
            canvas, lines[1][:16],
            (x1 + 10, y1 + int(ph * 0.65)),
            font, 0.42, (20, 20, 20) if sum(p_bgr) > 400 else (245, 245, 245), 1, cv2.LINE_AA
        )
    if len(lines) > 2:
        cv2.putText(
            canvas, lines[2][:18],
            (x1 + 10, y2 - 10),
            font, 0.38, (255, 255, 255), 1, cv2.LINE_AA
        )

    return canvas
