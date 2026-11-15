"""
KiranaVision — Standalone CLI Trainer for KiranaPacketCNN
Run: python vision/train_cnn.py
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.cnn_recognizer import recognizer
from vision.product_catalog import PRODUCT_CATALOG


def main():
    print("=" * 64)
    print("KiranaVision — Training 4-Stage PyTorch KiranaPacketCNN")
    print(f"Target Classes ({len(PRODUCT_CATALOG)} SKUs):")
    for item in PRODUCT_CATALOG:
        hero_tag = "[HERO]" if item.get("is_hero") else "      "
        print(f"  {hero_tag} {item['sku_id']} | {item['name']} (~{item['unit_weight_g']}g, Rs.{item['selling_price']})")
    print("=" * 64)

    metrics = recognizer.train_cnn_weights(epochs=24, samples_per_class=32)
    print(f"✅ Status:          {metrics['status']}")
    print(f"✅ Total Samples:   {metrics['samples']} augmented packet frames")
    print(f"✅ Final CE Loss:   {metrics['final_loss']}")
    print(f"✅ Train Accuracy:  {metrics['train_accuracy_pct']}%")
    print(f"✅ Elapsed Time:    {metrics['training_time_ms']} ms")
    print(f"✅ Saved Weights:   {metrics['weights_path']}")


if __name__ == "__main__":
    main()
