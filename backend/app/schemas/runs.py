from __future__ import annotations

import uuid

from pydantic import BaseModel


class StartRunResponse(BaseModel):
    run_id: uuid.UUID
    status: str
