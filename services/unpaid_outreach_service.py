"""
Controle do funil para usuários sem acesso: pitch + PIX imediato → ghosting 1h → novo ciclo.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Literal, Optional

from config import logger, DATA_DIR

OutreachAction = Literal['pitch_pix', 'ghost']

OUTREACH_FILE = os.path.join(DATA_DIR, "unpaid_outreach.json")
GHOSTING_HOURS = 1


class UnpaidOutreachService:
    def __init__(self, data_file: str = None):
        self.data_file = data_file or OUTREACH_FILE
        self._states: dict[int, dict] = {}
        os.makedirs(os.path.dirname(self.data_file) or ".", exist_ok=True)
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, encoding="utf-8") as f:
                    raw = json.load(f)
                self._states = {int(k): v for k, v in raw.items()}
        except Exception as e:
            logger.error(f"Erro ao carregar outreach de não pagantes: {e}")
            self._states = {}

    def _save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(
                    {str(k): v for k, v in self._states.items()},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.error(f"Erro ao salvar outreach de não pagantes: {e}")

    def _parse_ts(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        return datetime.fromisoformat(value)

    def _last_outreach_at(self, state: dict) -> Optional[datetime]:
        pix_at = self._parse_ts(state.get("pix_sent_at"))
        pitch_at = self._parse_ts(state.get("pitch_sent_at"))
        if pix_at and pitch_at:
            return max(pix_at, pitch_at)
        return pix_at or pitch_at

    def decide_action(self, user_id: int, now: Optional[datetime] = None) -> OutreachAction:
        now = now or datetime.now()
        state = self._states.get(user_id, {})
        last_at = self._last_outreach_at(state)

        if last_at is None:
            return "pitch_pix"

        if now - last_at < timedelta(hours=GHOSTING_HOURS):
            return "ghost"

        return "pitch_pix"

    def record_outreach(self, user_id: int, now: Optional[datetime] = None):
        """Registra envio simultâneo de pitch e PIX."""
        now = now or datetime.now()
        self._states[user_id] = {
            "pitch_sent_at": now.isoformat(),
            "pix_sent_at": now.isoformat(),
        }
        self._save()

    def record_pitch(self, user_id: int, now: Optional[datetime] = None):
        now = now or datetime.now()
        state = self._states.setdefault(user_id, {})
        state["pitch_sent_at"] = now.isoformat()
        self._save()

    def record_pix(self, user_id: int, now: Optional[datetime] = None):
        now = now or datetime.now()
        state = self._states.setdefault(user_id, {})
        state["pix_sent_at"] = now.isoformat()
        if not state.get("pitch_sent_at"):
            state["pitch_sent_at"] = now.isoformat()
        self._save()

    def clear_user(self, user_id: int):
        if user_id in self._states:
            del self._states[user_id]
            self._save()


unpaid_outreach_service = UnpaidOutreachService()
