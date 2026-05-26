import json
import logging
from pathlib import Path


def load_agent_guide_configs(agent_guide_md: Path) -> dict[str, dict]:
    """
    Extract inline JSON configurations from AGENT_GUIDE_LIST.md.

    The file contains lines like:
      * **JSON Configuration:** `{"repository_name":"...","detected_class":"..."}`
    """
    log = logging.LoggerAdapter(logging.getLogger("AgentGuideLoader"), {"component": "AgentGuideLoader"})
    if not agent_guide_md.exists():
        log.warning("Missing agent guide file: %s", agent_guide_md)
        return {}

    configs: dict[str, dict] = {}
    for raw_line in agent_guide_md.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if "**JSON Configuration:**" not in line:
            continue
        start = line.find("`")
        end = line.rfind("`")
        if start == -1 or end == -1 or end <= start:
            continue
        blob = line[start + 1 : end].strip()
        if not blob or blob == "N/A":
            continue
        if not (blob.startswith("{") and blob.endswith("}")):
            continue
        try:
            obj = json.loads(blob)
        except Exception:
            log.warning("Skipping unparsable JSON configuration line")
            continue
        if isinstance(obj, dict) and isinstance(obj.get("repository_name"), str) and obj["repository_name"]:
            configs[obj["repository_name"]] = obj
    return configs
