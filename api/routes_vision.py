"""
KiranaVision — FastAPI Routes for CNN + OpenCV Countertop & Weighing Machine Recognition
GET  /vision/catalog        — Product catalog enriched with live DB stock & reference thumbnails
POST /vision/detect         — Run OpenCV ROI + PyTorch CNN + Scale Weight Fusion on a frame
POST /vision/enroll         — Few-shot live webcam enrollment for a specific SKU
POST /vision/train          — Trigger PyTorch CNN training & return accuracy/loss metrics
POST /vision/commit-basket  — Deduct (checkout) or add (restock) detected packets in DB & notify Agent Book
"""
import base64
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.trace_bus import trace_bus
from db.database import get_db
from db.models import InventoryItem, Transaction
from vision.cnn_recognizer import recognizer
from vision.product_catalog import (
    HERO_SKUS,
    PRODUCT_CATALOG,
    get_product_by_sku,
    render_synthetic_packet,
)

router = APIRouter()

DEMO_MERCHANT_ID = "11111111-1111-1111-1111-111111111111"


class DetectFrameRequest(BaseModel):
    image_base64: str
    scale_weight_g: Optional[float] = None
    hint_skus: Optional[List[str]] = None
    merchant_id: str = DEMO_MERCHANT_ID


class EnrollPacketRequest(BaseModel):
    sku_id: str
    image_base64: str


class BasketCommitItem(BaseModel):
    sku_id: str
    quantity: int = 1


class CommitBasketRequest(BaseModel):
    mode: str = "checkout"  # "checkout" (STOCK OUT) or "restock" (STOCK IN)
    payment_mode: str = "upi"
    scale_weight_g: Optional[float] = None
    items: List[BasketCommitItem]
    merchant_id: str = DEMO_MERCHANT_ID


def _decode_data_uri(data_uri: str) -> bytes:
    if "," in data_uri:
        data_uri = data_uri.split(",", 1)[1]
    return base64.b64decode(data_uri)


@router.get("/catalog")
async def get_vision_catalog(
    merchant_id: str = DEMO_MERCHANT_ID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all 12 KiranaMate SKUs with their visual/physical metadata,
    live inventory quantities from the database, and OpenCV synthetic reference thumbnails.
    """
    r = await db.execute(
        select(InventoryItem).where(InventoryItem.merchant_id == merchant_id)
    )
    db_items = {item.sku_id: item for item in r.scalars().all()}

    now = datetime.utcnow()
    catalog_out = []
    for prod in PRODUCT_CATALOG:
        sku = prod["sku_id"]
        db_inv = db_items.get(sku)
        thumb_bgr = render_synthetic_packet(sku, 160, 160)
        thumb_b64 = recognizer.pipeline.encode_base64_jpeg(thumb_bgr, quality=84)

        days_to_expiry = (
            (db_inv.expiry_date - now).days
            if (db_inv and db_inv.expiry_date)
            else None
        )

        catalog_out.append({
            **prod,
            "current_stock": db_inv.quantity if db_inv else 0,
            "reorder_point": db_inv.reorder_point if db_inv else 10,
            "days_to_expiry": days_to_expiry,
            "prototypes_enrolled": len(recognizer.enrolled_embeddings.get(sku, [])),
            "thumbnail": thumb_b64,
        })

    return {
        "products": catalog_out,
        "hero_skus": HERO_SKUS,
        "total_classes": len(catalog_out),
        "model_arch": "KiranaPacketCNN (4-Stage PyTorch ConvNet + OpenCV HSV/ORB + Scale Sensor Fusion)",
    }


@router.post("/detect")
async def detect_counter_frame(
    req: DetectFrameRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Processes an overhead camera frame of the weighing scale or counter table:
    - Runs OpenCV CLAHE, motion-stability gate, and multi-contour segmentation
    - Classifies each packet via PyTorch KiranaPacketCNN + HSV/ORB + Scale Weight Fusion
    - Enriches detections with live database inventory counts
    """
    try:
        image_bytes = _decode_data_uri(req.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image payload: {e}")

    try:
        result = recognizer.detect_frame(
            image_bytes=image_bytes,
            scale_weight_g=req.scale_weight_g,
            hint_skus=req.hint_skus,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision pipeline error: {e}")

    # Enrich detected basket items with live DB inventory stock
    r = await db.execute(
        select(InventoryItem).where(InventoryItem.merchant_id == req.merchant_id)
    )
    stock_by_sku = {item.sku_id: item.quantity for item in r.scalars().all()}

    for b_item in result["basket"]:
        b_item["current_stock"] = stock_by_sku.get(b_item["sku_id"], 0)
    for det in result["detections"]:
        det["current_stock"] = stock_by_sku.get(det["sku_id"], 0)

    return result


@router.post("/enroll")
async def enroll_packet_frame(req: EnrollPacketRequest):
    """
    Few-shot live webcam enrollment: captures the packet currently on the counter/webcam
    and registers its 128-D CNN embedding + OpenCV spatial HSV/ORB descriptors.
    """
    try:
        image_bytes = _decode_data_uri(req.image_base64)
        res = recognizer.enroll_live_packet(req.sku_id, image_bytes)
        trace_bus.emit("vision_enroll", {
            "sku_id": req.sku_id,
            "name": res["name"],
            "prototypes_count": res["prototypes_count"],
        })
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrollment failed: {e}")


@router.post("/train")
async def trigger_cnn_training():
    """Re-trains the PyTorch KiranaPacketCNN on synthetic + augmented packet samples."""
    metrics = recognizer.train_cnn_weights(epochs=20, samples_per_class=28)
    return metrics


@router.post("/commit-basket")
async def commit_detected_basket(
    req: CommitBasketRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Commits the CNN-detected items placed on the weighing scale/table:
    - mode='checkout' (STOCK OUT): decrements InventoryItem.quantity and records Transaction(s)
    - mode='restock'  (STOCK IN):  increments InventoryItem.quantity
    Also broadcasts live telemetry to the Agent Book SSE stream (trace_bus).
    """
    if not req.items:
        raise HTTPException(status_code=400, detail="No items in basket to commit")

    r = await db.execute(
        select(InventoryItem).where(InventoryItem.merchant_id == req.merchant_id)
    )
    inv_map: Dict[str, InventoryItem] = {item.sku_id: item for item in r.scalars().all()}

    updated_items = []
    low_stock_alerts = []
    total_amount = 0.0
    now = datetime.utcnow()

    for b_item in req.items:
        prod = get_product_by_sku(b_item.sku_id)
        if not prod:
            continue
        inv = inv_map.get(b_item.sku_id)
        qty = max(1, int(b_item.quantity))
        line_amount = round(prod["selling_price"] * qty, 2)
        total_amount += line_amount

        prev_stock = inv.quantity if inv else 0
        if inv:
            if req.mode == "restock":
                inv.quantity = prev_stock + qty
            else:
                inv.quantity = max(0, prev_stock - qty)
            inv.updated_at = now
            new_stock = inv.quantity

            if req.mode == "checkout" and new_stock <= (inv.reorder_point or 10):
                low_stock_alerts.append({
                    "sku_id": inv.sku_id,
                    "name": inv.name,
                    "remaining_stock": new_stock,
                    "reorder_point": inv.reorder_point or 10,
                })
        else:
            new_stock = 0

        if req.mode == "checkout":
            txn = Transaction(
                merchant_id=uuid.UUID(str(req.merchant_id)),
                txn_id=f"VIS{uuid.uuid4().hex[:10].upper()}",
                amount=line_amount,
                category=prod["category"],
                sku_id=prod["sku_id"],
                payment_mode=req.payment_mode,
                txn_time=now,
            )
            db.add(txn)

        updated_items.append({
            "sku_id": prod["sku_id"],
            "name": prod["name"],
            "category": prod["category"],
            "quantity_delta": +qty if req.mode == "restock" else -qty,
            "previous_stock": prev_stock,
            "new_stock": new_stock,
            "line_amount": line_amount,
        })

    await db.commit()

    # Emit live trace and WhatsApp stream message to the Agent Book Command Center
    summary_names = ", ".join(
        f"{abs(i['quantity_delta'])}x {i['name']}" for i in updated_items
    )
    action_verb = "Restocked (+IN)" if req.mode == "restock" else "Checked Out (-OUT)"
    weight_note = f" [Scale: {int(round(req.scale_weight_g))}g]" if req.scale_weight_g else ""

    trace_bus.emit("vision_commit", {
        "mode": req.mode,
        "items": updated_items,
        "total_amount": round(total_amount, 2),
        "scale_weight_g": req.scale_weight_g,
        "low_stock_alerts": low_stock_alerts,
    })

    trace_bus.emit_wa_msg(
        "system-msg",
        f"📷 KiranaVision CNN Scale {action_verb}: {summary_names} (₹{total_amount:.0f}){weight_note}",
    )

    if low_stock_alerts:
        alert_str = ", ".join(
            f"{a['name']} ({a['remaining_stock']} left)" for a in low_stock_alerts
        )
        trace_bus.emit_wa_msg(
            "received",
            f"⚠️ *KiranaVision Low-Stock Alert*\nCounter camera detected stock drop below reorder point for: {alert_str}. Should I prepare a distributor reorder draft?",
        )

    return {
        "status": "committed",
        "mode": req.mode,
        "total_amount": round(total_amount, 2),
        "updated_items": updated_items,
        "low_stock_alerts": low_stock_alerts,
        "timestamp": now.isoformat(),
    }
