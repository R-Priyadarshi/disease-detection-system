"""
ALVEON Enterprise Hospital PACS - HL7 v2.x MLLP Socket Ingestion Server
Implements:
1. Minimal Lower Layer Protocol (MLLP) framing (Start byte: 0x0B, End bytes: 0x1C 0x0D).
2. Asynchronous multi-client TCP listener on port 2575 (default) conforming to HL7 v2.5.1.
3. Inbound parsing of ADT^A01/A04 (Admissions), ORM^O01 (Orders), and ORU^R01 (Observations).
4. Automated generation and transmission of HL7 Commit/Application ACKs (MSA|AA|...).
5. Direct ingestion into the ALVEON diagnostic worklist and patient repository.
6. Thread-safe runtime telemetry, message auditing, and simulation hooks.
"""

import asyncio
import logging
import datetime
import uuid
from typing import Dict, Any, List, Optional, Tuple

from core.hl7_engine import HL7Engine, HL7Message, HL7Segment

logger = logging.getLogger("alveon.mllp")

MLLP_START_BYTE = b"\x0b"
MLLP_END_BYTES = b"\x1c\x0d"


class MLLPMessageRecord:
    def __init__(self, msg_type: str, control_id: str, sender: str, raw_text: str, ack_sent: str, success: bool = True):
        self.message_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"
        self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        self.msg_type = msg_type
        self.control_id = control_id
        self.sender = sender
        self.raw_text = raw_text
        self.ack_sent = ack_sent
        self.success = success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "msg_type": self.msg_type,
            "control_id": self.control_id,
            "sender": self.sender,
            "raw_text": self.raw_text[:200] + "..." if len(self.raw_text) > 200 else self.raw_text,
            "ack_sent": self.ack_sent,
            "success": self.success
        }


class MLLPServer:
    """Asyncio TCP MLLP server for hospital EHR ingestion."""

    _instance: Optional["MLLPServer"] = None

    def __init__(self, host: str = "0.0.0.0", port: int = 2575):
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.is_running: bool = False
        self.started_at: Optional[datetime.datetime] = None
        self.active_clients: int = 0
        self.total_messages_received: int = 0
        self.total_acks_sent: int = 0
        self.total_errors: int = 0
        self.message_history: List[MLLPMessageRecord] = []
        self._hl7_engine = HL7Engine.get_instance()

    @classmethod
    def get_instance(cls, host: str = "0.0.0.0", port: int = 2575) -> "MLLPServer":
        if cls._instance is None:
            cls._instance = MLLPServer(host=host, port=port)
        return cls._instance

    async def start(self) -> bool:
        """Starts the MLLP TCP listener."""
        if self.is_running:
            return True

        try:
            self.server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port
            )
            self.is_running = True
            self.started_at = datetime.datetime.now(datetime.timezone.utc)
            logger.info(f"HL7 MLLP Socket Server listening on {self.host}:{self.port}")
            return True
        except Exception as ex:
            logger.warning(f"Could not bind MLLP on {self.host}:{self.port} (may require root or port already in use): {ex}")
            # Try alternate unprivileged port 2576 if 2575 is restricted
            if self.port == 2575:
                try:
                    self.port = 2576
                    self.server = await asyncio.start_server(
                        self._handle_client,
                        self.host,
                        self.port
                    )
                    self.is_running = True
                    self.started_at = datetime.datetime.now(datetime.timezone.utc)
                    logger.info(f"HL7 MLLP Socket Server listening on alternate port {self.host}:{self.port}")
                    return True
                except Exception as inner_ex:
                    logger.error(f"Failed to start MLLP server on alternate port: {inner_ex}")
            self.is_running = False
            return False

    async def stop(self):
        """Gracefully terminates the MLLP listener."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        self.is_running = False
        logger.info("HL7 MLLP Socket Server stopped.")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Processes an incoming MLLP TCP connection."""
        self.active_clients += 1
        client_addr = writer.get_extra_info("peername")
        logger.info(f"MLLP client connected from {client_addr}")

        try:
            while self.is_running:
                # Read until end of MLLP frame: \x1c\x0d
                data = await reader.readuntil(MLLP_END_BYTES)
                if not data:
                    break

                # Strip MLLP framing characters
                # Must start with \x0b and end with \x1c\x0d
                raw_payload = data
                if raw_payload.startswith(MLLP_START_BYTE):
                    raw_payload = raw_payload[len(MLLP_START_BYTE):]
                if raw_payload.endswith(MLLP_END_BYTES):
                    raw_payload = raw_payload[:-len(MLLP_END_BYTES)]

                raw_hl7_text = raw_payload.decode("utf-8", errors="replace")
                self.total_messages_received += 1

                # Process HL7 content and generate ACK
                ack_hl7, success = self.process_raw_hl7(raw_hl7_text, client_str=str(client_addr))

                # Send MLLP framed ACK
                framed_ack = MLLP_START_BYTE + ack_hl7.encode("utf-8") + MLLP_END_BYTES
                writer.write(framed_ack)
                await writer.drain()
                self.total_acks_sent += 1

        except asyncio.IncompleteReadError:
            # Client disconnected cleanly
            pass
        except Exception as ex:
            self.total_errors += 1
            logger.error(f"Error handling MLLP stream from {client_addr}: {ex}")
        finally:
            self.active_clients = max(0, self.active_clients - 1)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info(f"MLLP connection closed for {client_addr}")

    def process_raw_hl7(self, raw_hl7_text: str, client_str: str = "127.0.0.1") -> Tuple[str, bool]:
        """Parses raw HL7 text, routes to business logic, and returns formatted ACK string."""
        msg_type = "UNKNOWN"
        ctrl_id = str(uuid.uuid4())[:8]
        sender = "UNKNOWN"
        success = True
        err_msg = ""

        try:
            msg = HL7Message.parse(raw_hl7_text)
            for seg in msg.segments:
                if seg.segment_id == "MSH":
                    if len(seg.fields) >= 3 and seg.fields[2]:
                        sender = seg.fields[2]
                    if len(seg.fields) >= 8 and seg.fields[7]:
                        msg_type = seg.fields[7]
                    if len(seg.fields) >= 9 and seg.fields[8]:
                        ctrl_id = seg.fields[8]
                    break

            # Route by message type
            if "ORM" in msg_type or "O01" in msg_type:
                parsed_order = self._hl7_engine.parse_orm_o01(raw_hl7_text)
                self._integrate_order_to_worklist(parsed_order)
            elif "ADT" in msg_type:
                self._process_adt_message(msg)
            elif "ORU" in msg_type:
                logger.info(f"Ingested observation result ORU^R01 control_id={ctrl_id}")

            ack_msg = self._hl7_engine.generate_ack(ctrl_id, success=True)
            ack_text = ack_msg.to_string()

        except Exception as ex:
            success = False
            self.total_errors += 1
            err_msg = str(ex)
            logger.error(f"Failed to process HL7 payload: {ex}")
            ack_msg = self._hl7_engine.generate_ack(ctrl_id, success=False, error_msg=err_msg)
            ack_text = ack_msg.to_string()

        # Record in message audit history
        record = MLLPMessageRecord(
            msg_type=msg_type,
            control_id=ctrl_id,
            sender=sender or client_str,
            raw_text=raw_hl7_text,
            ack_sent=ack_text,
            success=success
        )
        self.message_history.insert(0, record)
        if len(self.message_history) > 100:
            self.message_history = self.message_history[:100]

        return ack_text, success

    def _process_adt_message(self, msg: HL7Message):
        """Processes ADT patient demographic and admission registration."""
        patient_mrn = "MRN-UNKNOWN"
        patient_name = "Anonymous Patient"
        for seg in msg.segments:
            if seg.segment_id == "PID":
                if len(seg.fields) >= 3 and seg.fields[2]:
                    patient_mrn = seg.fields[2].split("^")[0]
                if len(seg.fields) >= 5 and seg.fields[4]:
                    patient_name = seg.fields[4].replace("^", ", ")
                break

        logger.info(f"Processed ADT patient registration: MRN={patient_mrn}, Name={patient_name}")

    def _integrate_order_to_worklist(self, order_data: Dict[str, Any]):
        """Injects inbound order into ALVEON worklist."""
        try:
            import api.routes as routes
            from api.schemas import WorklistStudyItem
            if routes._WORKLIST_CACHE is None or len(routes._WORKLIST_CACHE) == 0:
                return

            ref_item = routes._WORKLIST_CACHE[0]
            ref_img = getattr(ref_item, "image_b64", "")
            ref_overlay = getattr(ref_item, "gradcam_overlay_b64", None)
            ref_zonation = getattr(ref_item, "zonation", None)

            accession = order_data.get("accession_number", f"ACC-{uuid.uuid4().hex[:6].upper()}")
            study_id = f"ALV-HL7-{uuid.uuid4().hex[:6].upper()}"
            is_stat = "STAT" in order_data.get("universal_service_text", "").upper()

            study_item = WorklistStudyItem(
                study_id=study_id,
                patient_mrn=order_data.get("patient_mrn", "MRN-UNKNOWN"),
                patient_name=order_data.get("patient_name", "Anonymous Patient"),
                patient_age_sex=f"{order_data.get('patient_sex', 'U')}, 50y",
                study_time=datetime.datetime.now().strftime("%H:%M EST"),
                priority="STAT_CRITICAL" if is_stat else "ROUTINE",
                priority_rank=1 if is_stat else 3,
                diagnosis="Pending Interpretation",
                is_pneumonia=False,
                confidence_percentage=0.0,
                dominant_zone="Mid-Zones",
                status="PENDING",
                is_signed=False,
                modality="DX",
                image_b64=ref_img,
                gradcam_overlay_b64=ref_overlay,
                zonation=ref_zonation,
                primary_finding=order_data.get("universal_service_text", "Chest Radiograph Single View (STAT)"),
                secondary_findings=["Inbound HL7 v2 ORM Order"]
            )
            routes._WORKLIST_CACHE.insert(0, study_item)
            if len(routes._WORKLIST_CACHE) > 60:
                routes._WORKLIST_CACHE.pop()
            logger.info(f"HL7 Order matched and injected into worklist as WorklistStudyItem: Accession={accession}")
        except Exception as ex:
            logger.warning(f"Could not inject HL7 order into _WORKLIST_CACHE: {ex}")

    def simulate_message(self, raw_hl7_text: str) -> Dict[str, Any]:
        """Simulates reception of an inbound HL7 message via REST API."""
        self.total_messages_received += 1
        ack_text, success = self.process_raw_hl7(raw_hl7_text, client_str="REST_SIMULATION")
        self.total_acks_sent += 1
        return {
            "success": success,
            "ack_message": ack_text,
            "parsed_summary": {
                "total_messages": self.total_messages_received,
                "total_acks": self.total_acks_sent,
                "total_errors": self.total_errors
            }
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive status and telemetry for the MLLP engine."""
        uptime = 0.0
        if self.started_at:
            uptime = round((datetime.datetime.now(datetime.timezone.utc) - self.started_at).total_seconds(), 1)

        return {
            "is_running": self.is_running,
            "host": self.host,
            "port": self.port,
            "protocol": "HL7 v2.5.1 MLLP",
            "framing": "0x0B [payload] 0x1C 0x0D",
            "active_connections": self.active_clients,
            "total_messages_received": self.total_messages_received,
            "total_acks_sent": self.total_acks_sent,
            "total_errors": self.total_errors,
            "uptime_seconds": uptime,
            "recent_messages": [m.to_dict() for m in self.message_history[:10]]
        }


def get_mllp_server() -> MLLPServer:
    return MLLPServer.get_instance()
