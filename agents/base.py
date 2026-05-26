class AgentBase:
    def __init__(self, role: str, config: dict | None = None) -> None:
        self.role = role
        self.config = config or {}
