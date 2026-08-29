"""
Mock E-Commerce Service for Order Tracking, Returns, and Refunds.
Provides deterministic order lookups for key demo IDs and procedural generation for any order ID,
including live GPS coordinates and transit route map telemetry.
"""

import random
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

class EcommerceService:
    def __init__(self):
        # Predefined demo orders with rich realistic details and GPS coordinates
        now = datetime.now(timezone.utc)
        self._preset_orders: Dict[str, Dict[str, Any]] = {
            "QD-1234": {
                "order_id": "#QD-1234",
                "customer_name": "Alex Johnson",
                "status": "In Transit",
                "carrier": "FedEx Express",
                "tracking_number": "FDX-884920194",
                "items": ["Ergonomic Mechanical Keyboard (RGB)", "Braided USB-C Cable (2m)"],
                "total_amount": "$129.99",
                "order_date": (now - timedelta(days=2)).strftime("%b %d, %Y"),
                "estimated_delivery": (now + timedelta(days=1)).strftime("%A, %b %d"),
                "current_location": "Distribution Center, Chicago, IL",
                "timeline": [
                    {"time": "2 days ago", "event": "Order placed & confirmed"},
                    {"time": "Yesterday at 4:15 PM", "event": "Departed warehouse in Columbus, OH"},
                    {"time": "Today at 6:30 AM", "event": "Arrived at sorting facility in Chicago, IL"},
                    {"time": "Expected tomorrow", "event": "Out for delivery by 7:00 PM"}
                ],
                "map_telemetry": {
                    "origin": "Columbus, OH (Depot A)",
                    "current": "Chicago, IL (Sort Facility)",
                    "destination": "Minneapolis, MN (Customer Home)",
                    "progress_percent": 68
                },
                "return_eligible": True,
                "refund_status": "No refund requested"
            },
            "QD-4567": {
                "order_id": "#QD-4567",
                "customer_name": "Jordan Smith",
                "status": "Refund Approved",
                "carrier": "UPS Ground",
                "tracking_number": "1Z882910399102",
                "items": ["Premium Noise-Cancelling Headphones"],
                "total_amount": "$179.00",
                "order_date": (now - timedelta(days=5)).strftime("%b %d, %Y"),
                "estimated_delivery": "Delivered 3 days ago",
                "current_location": "Return Warehouse, Austin, TX",
                "timeline": [
                    {"time": "5 days ago", "event": "Order delivered"},
                    {"time": "2 days ago", "event": "Return received at warehouse"},
                    {"time": "Yesterday", "event": "Refund Approved & Processed to original payment method"}
                ],
                "map_telemetry": {
                    "origin": "Return Facility, Austin, TX",
                    "current": "Processed",
                    "destination": "Bank Settlement",
                    "progress_percent": 100
                },
                "return_eligible": False,
                "refund_status": "Refund Approved - $179.00 Processed"
            },
            "QD-5678": {
                "order_id": "#QD-5678",
                "customer_name": "Samantha Lee",
                "status": "Out for Delivery",
                "carrier": "UPS Ground",
                "tracking_number": "1Z9999999999999999",
                "items": ["Noise Cancelling Wireless Headphones - Midnight Black"],
                "total_amount": "$249.50",
                "order_date": (now - timedelta(days=3)).strftime("%b %d, %Y"),
                "estimated_delivery": "Today by 4:30 PM",
                "current_location": "Local Delivery Van, Austin, TX",
                "timeline": [
                    {"time": "3 days ago", "event": "Order placed & verified"},
                    {"time": "2 days ago", "event": "Shipped from Dallas, TX hub"},
                    {"time": "Today at 7:45 AM", "event": "Loaded onto delivery vehicle in Austin, TX"},
                    {"time": "Today", "event": "Out for delivery (Driver is 4 stops away)"}
                ],
                "map_telemetry": {
                    "origin": "Dallas, TX (Logistics Hub)",
                    "current": "Austin, TX (Courier Van #42)",
                    "destination": "Downtown Austin, TX (Customer Address)",
                    "progress_percent": 92
                },
                "return_eligible": True,
                "refund_status": "No refund requested"
            },
            "QD-9012": {
                "order_id": "#QD-9012",
                "customer_name": "Marcus Vance",
                "status": "Delivered",
                "carrier": "DHL Express",
                "tracking_number": "DHL-440219842",
                "items": ["Ultra-Wide 34' Curved Monitor 144Hz"],
                "total_amount": "$499.00",
                "order_date": (now - timedelta(days=6)).strftime("%b %d, %Y"),
                "estimated_delivery": "Delivered 2 days ago",
                "current_location": "Delivered (Front Porch), Seattle, WA",
                "timeline": [
                    {"time": "6 days ago", "event": "Order verified"},
                    {"time": "4 days ago", "event": "Processed through Seattle customs hub"},
                    {"time": "2 days ago", "event": "Delivered to Front Door, Seattle, WA"}
                ],
                "map_telemetry": {
                    "origin": "San Jose, CA",
                    "current": "Seattle, WA (Delivered)",
                    "destination": "Seattle, WA (Customer)",
                    "progress_percent": 100
                },
                "return_eligible": True,
                "refund_status": "Refund $499.00 Available upon return"
            }
        }

    def _normalize_id(self, order_id: Optional[str]) -> str:
        if not order_id or not isinstance(order_id, str):
            return "QD-1234"
        clean = order_id.upper().strip().replace("#", "").replace("ORDER", "").replace("-", "").strip()
        if clean.startswith("ORD"):
            clean = clean[3:]
        if clean.startswith("QD"):
            return f"QD-{clean[2:]}"
        return f"QD-{clean}" if clean else "QD-1234"

    def lookup_order(self, order_id_or_input: str) -> Dict[str, Any]:
        """Look up order by ID or synthesize a deterministic realistic order."""
        clean_id = self._normalize_id(order_id_or_input)
        
        if clean_id in self._preset_orders:
            return self._preset_orders[clean_id]
        
        # Deterministic generation using SHA256 seed
        seed_val = int(hashlib.sha256(clean_id.encode('utf-8')).hexdigest()[:8], 16)
        rng = random.Random(seed_val)
        
        statuses = ["In Transit", "Out for Delivery", "Shipped", "Processing in Hub"]
        carriers = ["FedEx Express", "UPS Ground", "DHL Global Mail", "USPS Priority"]
        cities = ["Atlanta, GA", "Denver, CO", "Phoenix, AZ", "Boston, MA", "Seattle, WA", "Dallas, TX"]
        products = [
            "Smart Home Security Hub v2",
            "Compact Espresso Maker",
            "Wireless Ergonomic Mouse",
            "4K Ultra-HD Webcam with Privacy Shutter",
            "High-Speed 65W GaN Charger"
        ]
        
        status = rng.choice(statuses)
        carrier = rng.choice(carriers)
        city = rng.choice(cities)
        item = rng.choice(products)
        amount = f"${rng.randint(29, 299)}.{rng.choice(['00', '50', '99'])}"
        progress = rng.randint(40, 85)
        now = datetime.now(timezone.utc)
        
        return {
            "order_id": f"#{clean_id}",
            "customer_name": "Valued Customer",
            "status": status,
            "carrier": carrier,
            "tracking_number": f"{carrier[:3].upper()}-{rng.randint(100000000, 999999999)}",
            "items": [item],
            "total_amount": amount,
            "order_date": (now - timedelta(days=rng.randint(1, 4))).strftime("%b %d, %Y"),
            "estimated_delivery": (now + timedelta(days=rng.randint(1, 3))).strftime("%A, %b %d"),
            "current_location": f"Regional Sort Facility, {city}",
            "timeline": [
                {"time": "Order confirmed", "event": "Payment approved & verified"},
                {"time": "In Transit", "event": f"Departed regional hub via {carrier}"},
                {"time": "Next step", "event": f"Delivery scheduled to your destination"}
            ],
            "map_telemetry": {
                "origin": "Main Warehouse Hub",
                "current": f"{city} (Sort Facility)",
                "destination": "Customer Delivery Address",
                "progress_percent": progress
            },
            "return_eligible": True,
            "refund_status": "No refund requested"
        }

    def check_refund_status(self, order_id_or_email: str) -> Dict[str, Any]:
        """Check the status of a refund."""
        clean = self._normalize_id(order_id_or_email)
        if clean in self._preset_orders and "Refund" in self._preset_orders[clean]["status"]:
            return {
                "order_id": clean,
                "status": "Refund Approved & Processed",
                "amount": self._preset_orders[clean]["total_amount"],
                "message": f"Good news! The refund of {self._preset_orders[clean]['total_amount']} for {clean} has been processed back to your original payment method. Please allow 2-4 business days for your bank to post the credit."
            }
        
        order = self.lookup_order(order_id_or_email)
        return {
            "order_id": order["order_id"],
            "status": "Pending Inspection / In Transit",
            "amount": order["total_amount"],
            "message": f"Refund record found for order {order['order_id']} ({order['total_amount']}). Once your returned item arrives at our warehouse and passes safety inspection, your refund will be automatically credited within 48 hours."
        }

    def process_return(self, order_id: str, reason: str) -> Dict[str, Any]:
        """Generate a return label and return confirmation."""
        order = self.lookup_order(order_id)
        label_id = f"RET-{random.randint(100000, 999999)}"
        return {
            "order_id": order["order_id"],
            "label_id": label_id,
            "carrier": order["carrier"],
            "items": order["items"],
            "reason": reason,
            "return_window_days": 14,
            "message": f"Return approved for {order['order_id']} (Reason: {reason}). Prepaid return label #{label_id} has been emailed to your account. Please affix the label and drop the package off with {order['carrier']} within 14 days."
        }

    def get_catalog(self, query: Optional[str] = None) -> list[dict]:
        """Return structured product catalog with specs, pricing, and ratings."""
        catalog = [
            {
                "id": "PROD-KB01",
                "emoji": "⌨️",
                "name": "Apex Pro Mechanical Keyboard",
                "category": "Keyboards",
                "price": "$129.99",
                "rating": 4.9,
                "reviews_count": "1.4k",
                "badge": "Best Seller",
                "specs": ["RGB Backlit", "Hot-Swappable", "PBT Keycaps", "USB-C"],
                "stock": "In Stock",
                "description": "Ergonomic tactile mechanical switches with aircraft-grade aluminum chassis."
            },
            {
                "id": "PROD-HP02",
                "emoji": "🎧",
                "name": "CloudAir Wireless ANC Headphones",
                "category": "Audio",
                "price": "$249.50",
                "rating": 4.8,
                "reviews_count": "890",
                "badge": "Top Rated",
                "specs": ["Active Noise Cancelling", "40hr Battery", "Lossless BT 5.3", "Built-in Mic"],
                "stock": "In Stock",
                "description": "Studio-grade lossless wireless audio with 40dB hybrid noise reduction."
            },
            {
                "id": "PROD-MN03",
                "emoji": "🖥️",
                "name": "CurvView 34\" Ultra-Wide Monitor",
                "category": "Displays",
                "price": "$499.00",
                "rating": 4.9,
                "reviews_count": "620",
                "badge": "Editor's Choice",
                "specs": ["3440x1440 WQHD", "144Hz Refresh", "1ms IPS HDR400", "USB-C Hub 90W"],
                "stock": "In Stock",
                "description": "Immersive 1500R curvature with sRGB 99% color accuracy for work & gaming."
            },
            {
                "id": "PROD-MS04",
                "emoji": "🖱️",
                "name": "PrecisionGlide Vertical Wireless Mouse",
                "category": "Mice",
                "price": "$69.00",
                "rating": 4.7,
                "reviews_count": "2.1k",
                "badge": "Ergonomic Pick",
                "specs": ["57° Natural Grip", "Silent Clicks", "4000 DPI Sensor", "Multi-Device Flow"],
                "stock": "In Stock",
                "description": "Natural handshake position reduces wrist and forearm muscle strain."
            },
            {
                "id": "PROD-CH05",
                "emoji": "⚡",
                "name": "VoltFlow 65W GaN Fast Charger",
                "category": "Accessories",
                "price": "$39.99",
                "rating": 4.9,
                "reviews_count": "3.5k",
                "badge": "Essentials",
                "specs": ["2x USB-C + 1x USB-A", "GaN III Tech", "Foldable Prongs", "Laptop Compatible"],
                "stock": "In Stock",
                "description": "Ultra-compact high-speed charging for laptops, phones, and tablets simultaneously."
            }
        ]
        if not query:
            return catalog
        q = query.lower().strip()
        # Direct exact match
        direct = [
            p for p in catalog
            if q in p["name"].lower()
            or q in p["category"].lower()
            or any(q in s.lower() for s in p["specs"])
        ]
        if direct:
            return direct
        
        # Token-based keyword matching (e.g. "suggest a monitor" -> matches "monitor")
        stopwords = {
            "suggest", "recommend", "show", "me", "a", "an", "the", "what", "are", "do", "you",
            "have", "best", "popular", "gear", "items", "products", "product", "buy", "good",
            "and", "or", "for", "with", "all", "in", "on", "of", "to", "is", "it", "at", "by",
            "from", "as", "can", "will", "our", "your", "any", "some", "top", "catalog", "selection"
        }
        tokens = [t for t in q.replace('?', '').replace('!', '').replace('.', '').replace(',', '').split() if t not in stopwords and len(t) > 2]
        
        if tokens:
            token_matches = [
                p for p in catalog
                if any(
                    t in p["name"].lower()
                    or t in p["category"].lower()
                    or any(t in s.lower() for s in p["specs"])
                    for t in tokens
                )
            ]
            if token_matches:
                return token_matches

        return catalog
