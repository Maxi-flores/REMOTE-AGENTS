# Strategic Mission Generation Engine (Phase 19)

## Status

Phase 19 is complete as an advisory-only layer.

## Purpose

Strategic Mission Generation Engine (SMGE) converts executive briefing findings into deterministic strategic mission recommendations.

It consumes:

- `.control_plane/executive/executive_briefing.json` (or a provided briefing path)

It produces:

- ranked advisory mission candidates
- recommended sequence
- summary metrics

## Safety Boundary

SMGE does not:

- execute agents or tasks
- enqueue to `.platform_queue/next_task.json`
- modify repositories
- enforce policies or gates
- change runtime behavior

Outputs are optional and written only under:

- `.control_plane/strategic_missions/`

## CLI

```bash
python src/strategic_missions/cli.py --print
python src/strategic_missions/cli.py --export
python src/strategic_missions/cli.py --export-jsonl
python src/strategic_missions/cli.py --from-briefing ".control_plane/executive/executive_briefing.json" --limit 5 --print
```

