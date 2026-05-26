import logging


class _OfficeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "component"):
            record.component = "-"
        if not hasattr(record, "handshake_hash"):
            record.handshake_hash = "-"
        return super().format(record)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        _OfficeFormatter(
            fmt="%(asctime)s %(levelname)s [%(component)s] [twin:%(handshake_hash)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    )
    root.addHandler(handler)


def component_logger(component: str) -> logging.LoggerAdapter:
    return logging.LoggerAdapter(logging.getLogger(component), {"component": component})
