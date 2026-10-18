#!/usr/bin/env python3
"""
Sanitizes all frontend HTML files, vajra-bridge.js, and README.md
to strictly enforce PS 26249 requirements:
- Generic aircraft names: Transport-A, Fighter-B, Trainer-C, Heli-D
- Generic engine models: Turbofan-TF1, Turboshaft-TS1
- Generic base designations: Base 01, Base 02, Base 03, Base 04, Base 05
- Generic user roles: Fleet Commander, Maintenance Officer, Analyst
- Removal of real platform designations, real places, real people names, military ranks,
  and fake classification jargon (FIPS-140, SECURITY LEVEL-4, AIR-GAP ISOLATED, etc.).
"""

import os
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "stitch_vajra_fleet_maintenance_platform"

REPLACEMENTS = [
    # 1. Base names and locations (Longer patterns first)
    (r"Air Force Station Ambala", "Base 01"),
    (r"Air Force Station Pune", "Base 02"),
    (r"Air Force Station Jodhpur", "Base 03"),
    (r"Air Force Station Tezpur", "Base 04"),
    (r"Air Force Station Bengaluru \(BRD\)", "Base 05"),
    (r"Air Force Station Bengaluru", "Base 05"),
    (r"AFS Ambala \(Base 01\)", "Base 01"),
    (r"AFS Halwara \(Base 02\)", "Base 02"),
    (r"AFS Gwalior \(Base 03\)", "Base 03"),
    (r"AFS Bareilly \(Base 04\)", "Base 04"),
    (r"AFS Sulur \(Base 05\)", "Base 05"),
    (r"Base 01 \(Ambala Sector\)", "Base 01"),
    (r"Base 01 \(Ambala\)", "Base 01"),
    (r"Base 02 \(Halwara\)", "Base 02"),
    (r"Base 03 \(Gwalior\)", "Base 03"),
    (r"Base 04 \(Bareilly\)", "Base 04"),
    (r"Base 05 \(Sulur\)", "Base 05"),
    (r"Ambala \(17 Sqn Golden Arrows\)", "Base 01 (Forward Sector)"),
    (r"Halwara \(220 Sqn Desert Tigers\)", "Base 02 (Interceptor Hub)"),
    (r"Gwalior \(1 Sqn Tigers\)", "Base 03 (Central Depot)"),
    (r"Bareilly \(24 Sqn Hunting Hawks\)", "Base 04 (Air Superiority Depot)"),
    (r"Sulur \(45 Sqn Flying Daggers\)", "Base 05 (Maritime Forward Reserve)"),
    (r"AFS Ambala", "Base 01"),
    (r"AFS Halwara", "Base 02"),
    (r"AFS Gwalior", "Base 03"),
    (r"AFS Bareilly", "Base 04"),
    (r"AFS Sulur", "Base 05"),
    (r"\bAmbala\b", "Base 01"),
    (r"\bHalwara\b", "Base 02"),
    (r"\bGwalior\b", "Base 03"),
    (r"\bBareilly\b", "Base 04"),
    (r"\bSulur\b", "Base 05"),

    # 2. Aircraft & Engine designations
    (r"Su-30MKI", "Fighter-B"),
    (r"Su-30 MKI", "Fighter-B"),
    (r"Su-30", "Fighter-B"),
    (r"C-17 Globemaster", "Transport-A"),
    (r"C-17", "Transport-A"),
    (r"Hawk Mk132", "Trainer-C"),
    (r"Hawk Mk\.132", "Trainer-C"),
    (r"Hawk Mk 132", "Trainer-C"),
    (r"LCH Prachand", "Heli-D"),
    (r"AL-31FP", "Turbofan-TF1"),
    (r"Shakti-1H1", "Turboshaft-TS1"),

    # 3. People & Military Ranks
    (r"Air Marshal Vikram Singh", "Fleet Commander"),
    (r"Air Commodore V\. Sharma", "Fleet Commander"),
    (r"Air Commodore", "Fleet Commander"),
    (r"Wing Commander Rajesh Sharma", "Maintenance Officer"),
    (r"Wing Commander R\. Pillai", "Maintenance Officer"),
    (r"Wing Commander", "Maintenance Officer"),
    (r"Wg Cdr Rajesh Sharma", "Maintenance Officer"),
    (r"Wg Cdr R\. Pillai", "Maintenance Officer"),
    (r"Wg Cdr", "Fleet Commander"),
    (r"Squadron Leader Priya Nair", "Analyst"),
    (r"Squadron Leader A\. Gupta", "Analyst"),
    (r"Squadron Leader", "Analyst"),
    (r"Sqn Ldr Priya Nair", "Analyst"),
    (r"Sqn Ldr A\. Gupta", "Analyst"),
    (r"Sqn Ldr", "Analyst"),
    (r"Air Mshl", "Fleet Commander"),
    (r"Air HQ", "Fleet Command HQ"),

    # 4. Fake security & classification jargon
    (r"AIR-GAP ISOLATED", "OFFLINE LOCAL NODE"),
    (r"AIR-GAP ENFORCED", "OFFLINE LOCAL ENCLAVE"),
    (r"SECURITY LEVEL-4", "SYSTEM NODE-01"),
    (r"CIPHER: AES-256-GCM-AIRGAP", "SYSTEM INTEGRITY: VERIFIED"),
    (r"HSM REV: 4\.8\.1-RELEASE", "SYSTEM REV: 2.4.0-OFFLINE"),
    (r"FIPS-140", "SECURITY PROTOCOL"),
    (r"Local HSM: VERIFIED", "Security Check: PASSED"),
    (r"RESTRICTED ACCESS", "AUTHORIZED ACCESS ONLY"),
    (r"local hardware HSM node ledger", "immutable audit ledger"),
    (r"hardware HSM node ledger", "immutable audit ledger"),
    (r"hardware HSM", "audit ledger"),
    (r"Air HQ telemetry", "fleet command telemetry"),
]

def sanitize_file(file_path: Path):
    if not file_path.exists():
        return
    text = file_path.read_text(encoding="utf-8")
    original_text = text
    
    for pattern, replacement in REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
        
    if text != original_text:
        file_path.write_text(text, encoding="utf-8")
        print(f"Sanitized: {file_path.relative_to(ROOT_DIR)}")

def main():
    print("Sanitizing frontend HTML screens...")
    for html_file in FRONTEND_DIR.glob("**/code.html"):
        sanitize_file(html_file)
        
    print("Sanitizing vajra-bridge.js...")
    sanitize_file(FRONTEND_DIR / "vajra-bridge.js")
    
    print("Sanitizing README.md...")
    sanitize_file(ROOT_DIR / "README.md")
    
    print("Sanitization complete.")

if __name__ == "__main__":
    main()
