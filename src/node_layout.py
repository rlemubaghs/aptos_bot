from dataclasses import dataclass
from typing import List, Optional

from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class NodeList:
    tg_chat_id: int
    ip: str
    api_port: Optional[int] = 8080
    metrics_port: Optional[int] = 9101
    seed_port: Optional[int] = 6180
    status: Optional[bool] = None
    modified: Optional[int] = 0
    checked: Optional[int] = 0
    errors: Optional[List[str]] = None
    alarm_sent: Optional[int] = 0

    def __str__(self) -> str:
        if self.status is None:
            return f'{self.ip} - Unknown status'
        if self.status:
            return f'{self.ip} - Running'
        if ~self.status:
            return '\n'.join(f'{self.ip} - Error: {error}' for error in self.errors)
