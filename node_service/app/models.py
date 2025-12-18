from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class LocalRoom:
    code: str
    title: Optional[str] = None
    max_participants: int = 20
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class NodeState:
    rooms: Dict[str, LocalRoom] = field(default_factory=dict)

    cpu_load: float | None = None
    mem_load: float | None = None

    def active_rooms_count(self) -> int:
        return sum(1 for r in self.rooms.values() if r.is_active)


# Глобальный объект состояния для этой ноды
node_state = NodeState()
