#!/usr/bin/env python3
"""
================================================================================
INTERNAL REFINERY TOOL: SCADA MODBUS TELEMETRY PACKET PARSER & ANOMALY DETECTOR
Classification: INTERNAL REFINERY OT AUTOMATION // AIR-GAPPED
Purpose: Parses Modbus-RTU / TCP industrial sensor telemetry frames, performs
         CRC-16 validation, converts raw ADC counts to engineering units,
         and detects operational excursion thresholds.
================================================================================
"""

import struct
import json
import logging
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def calculate_crc16_modbus(data: bytes) -> int:
    """
    Calculate standard Modbus CRC-16 (Polynomial: 0xA001, Initial: 0xFFFF).
    Used to verify data integrity over RS-485 / serial lines in harsh electrical environments.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


class ScadaModbusFrameParser:
    """
    Parser for industrial refinery distributed control system (DCS) telemetry packets.
    """

    def __init__(self, register_map_file: Optional[str] = None):
        self.register_map = {
            30001: {"tag": "PT-101", "name": "Crude Feed Suction Pressure", "unit": "barg", "scale": 0.01, "alarm_high": 35.0},
            30002: {"tag": "TT-102", "name": "Crude Pre-heat Temperature", "unit": "degC", "scale": 0.1, "alarm_high": 240.0},
            30003: {"tag": "FT-103", "name": "Charge Pump Discharge Flow", "unit": "m3/hr", "scale": 0.1, "alarm_low": 40.0},
            30004: {"tag": "VT-104", "name": "Pump 11-P-101A DE Vibration", "unit": "mm/s RMS", "scale": 0.01, "alarm_high": 7.1},
            30005: {"tag": "LT-105", "name": "Separator Liquid Level", "unit": "%", "scale": 0.1, "alarm_high": 85.0}
        }
        if register_map_file:
            self._load_register_map(register_map_file)

    def _load_register_map(self, filepath: str):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.register_map = {int(k): v for k, v in data.get("registers", {}).items()}
                logging.info(f"Loaded {len(self.register_map)} register definitions from {filepath}")
        except Exception as e:
            logging.warning(f"Could not load custom register map: {e}, falling back to defaults.")

    def parse_modbus_rtu_frame(self, raw_frame_hex: str) -> Dict[str, Any]:
        """
        Parse raw hex string representing a Modbus-RTU Response Packet (Function Code 04 / 03):
        [Slave ID (1B)][Function Code (1B)][Byte Count (1B)][Register Data (N*2 B)][CRC Low (1B)][CRC High (1B)]
        """
        raw_bytes = bytes.fromhex(raw_frame_hex.replace(" ", ""))

        if len(raw_bytes) < 5:
            raise ValueError(f"Packet too short ({len(raw_bytes)} bytes). Minimum 5 bytes required.")

        payload = raw_bytes[:-2]
        received_crc = raw_bytes[-2] | (raw_bytes[-1] << 8)
        calculated_crc = calculate_crc16_modbus(payload)

        crc_valid = (received_crc == calculated_crc)
        if not crc_valid:
            logging.error(f"CRC Mismatch! Received: 0x{received_crc:04X}, Calculated: 0x{calculated_crc:04X}")

        slave_id = payload[0]
        function_code = payload[1]
        byte_count = payload[2]
        data_bytes = payload[3:3 + byte_count]

        num_registers = byte_count // 2
        raw_registers = struct.unpack(f">{num_registers}H", data_bytes)

        parsed_readings = []
        anomalies_detected = []

        start_reg = 30001
        for i, val in enumerate(raw_registers):
            reg_address = start_reg + i
            meta = self.register_map.get(reg_address, {
                "tag": f"REG_{reg_address}",
                "name": "Unknown Parameter",
                "unit": "raw",
                "scale": 1.0,
                "alarm_high": None,
                "alarm_low": None
            })

            scaled_val = round(val * meta.get("scale", 1.0), 3)
            status = "NORMAL"

            # Check threshold alarms
            if meta.get("alarm_high") is not None and scaled_val > meta["alarm_high"]:
                status = "HIGH_ALARM"
                anomalies_detected.append({
                    "tag": meta["tag"],
                    "value": scaled_val,
                    "threshold": meta["alarm_high"],
                    "condition": "EXCEEDED_HIGH_LIMIT"
                })
            elif meta.get("alarm_low") is not None and scaled_val < meta["alarm_low"]:
                status = "LOW_ALARM"
                anomalies_detected.append({
                    "tag": meta["tag"],
                    "value": scaled_val,
                    "threshold": meta["alarm_low"],
                    "condition": "BELOW_LOW_LIMIT"
                })

            parsed_readings.append({
                "register": reg_address,
                "tag": meta["tag"],
                "description": meta["name"],
                "raw_counts": val,
                "engineering_value": scaled_val,
                "unit": meta["unit"],
                "status": status
            })

        return {
            "slave_id": slave_id,
            "function_code": function_code,
            "crc_valid": crc_valid,
            "readings": parsed_readings,
            "anomalies_count": len(anomalies_detected),
            "anomalies": anomalies_detected
        }


def sample_telemetry_batch() -> List[str]:
    """Returns sample raw hex frames simulating live DCS transmission."""
    # Frame 1: Normal operating conditions
    # Slave 01, Func 04, 10 bytes (5 registers), values: 28.5 barg, 185.0 C, 120.5 m3/h, 2.15 mm/s, 54.0%
    # Frame 2: Anomaly case (vibration 8.42 mm/s > 7.1 trip limit)
    return [
        "01 04 0A 0B 22 07 3A 04 B5 00 D7 02 1C 5B F1",
        "01 04 0A 0C 1A 07 6C 04 90 03 4A 02 30 7A 19"
    ]


if __name__ == "__main__":
    parser = ScadaModbusFrameParser()
    frames = sample_telemetry_batch()
    
    print("=" * 70)
    print("AIR-GAPPED SCADA TELEMETRY PARSER OUTPUT")
    print("=" * 70)
    for idx, frame in enumerate(frames, 1):
        print(f"\n--- Processing Frame #{idx}: {frame} ---")
        result = parser.parse_modbus_rtu_frame(frame)
        print(f"Slave ID: {result['slave_id']} | CRC Status: {'VALID' if result['crc_valid'] else 'CORRUPT'}")
        for r in result["readings"]:
            flag = f" [!] {r['status']}" if r['status'] != "NORMAL" else ""
            print(f"  [{r['tag']:<8}] {r['description']:<32}: {r['engineering_value']} {r['unit']}{flag}")
        if result["anomalies"]:
            print(f"  >>> ALERT: {len(result['anomalies'])} operational excursions detected!")
    print("\n" + "=" * 70)
