import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from pico import Pico, SessionStore, WorkspaceContext
from pico.testing import ScriptedModelClient


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT / "demo-workspace"
SUMMARY_PATH = ROOT / "trace-tracking-summary.json"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def relative(path):
    return Path(path).resolve().relative_to(WORKSPACE.resolve()).as_posix()


def main():
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)
    WORKSPACE.mkdir(parents=True)
    (WORKSPACE / "README.md").write_text("trace tracking workspace\n", encoding="utf-8")
    (WORKSPACE / "facts.txt").write_text(
        "alpha\n"
        "deploy key is red\n"
        "memory demos should be deterministic\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=WORKSPACE, check=True)

    sessions_dir = WORKSPACE / ".pico" / "sessions"
    sessions_dir.mkdir(parents=True)
    for index in range(2):
        (sessions_dir / f"older-{index}.json").write_text(
            json.dumps({"id": f"older-{index}", "history": []}) + "\n",
            encoding="utf-8",
        )

    workspace = WorkspaceContext.build(WORKSPACE, repo_root_override=WORKSPACE)
    store = SessionStore(sessions_dir)
    agent = Pico(
        model_client=ScriptedModelClient(
            [
                '<tool>{"name":"read_file","args":{"path":"facts.txt","start":1,"end":20}}</tool>',
                "<final>Read facts. <memory>Project: deploy key is red.</memory></final>",
                '<tool>{"name":"read_file","args":{"path":".pico/memory/MEMORY.md","start":1,"end":80}}</tool>',
                '<tool>{"name":"write_file","args":{"path":".pico/memory/topics/project.md","content":"# Project Memory\\n\\n- topic: project\\n- summary: Stable facts from trace tracking.\\n- tags: project, trace\\n- updated_at: 2026-06-24T15:30:00+08:00\\n\\n## Notes\\n- deploy key is red\\n"}}</tool>',
                '<tool>{"name":"write_file","args":{"path":".pico/memory/MEMORY.md","content":"# Durable Memory Index\\n\\n- [Project Memory](topics/project.md): Stable facts from trace tracking\\n"}}</tool>',
                "<final>Dream consolidated project memory.</final>",
            ]
        ),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        auto_dream=True,
        dream_min_sessions=2,
        dream_interval_hours=0,
        max_steps=10,
    )

    answer = agent.ask("Read facts.txt once and remember the stable deploy fact.")
    agent.wait_for_memory_maintenance(timeout=10)

    run_dir = Path(agent.current_run_dir)
    report = read_json(run_dir / "report.json")
    trace = read_jsonl(run_dir / "trace.jsonl")
    session_path = agent.session_store.path(agent.session["id"])
    session = read_json(session_path)
    events = read_jsonl(agent.session_event_bus.path)

    memory_root = WORKSPACE / ".pico" / "memory"
    memory_files = {}
    for path in sorted(memory_root.rglob("*")):
        if path.is_file():
            memory_files[relative(path)] = path.read_text(encoding="utf-8", errors="replace")

    prompt_after = agent.prompt("Recall the deploy fact from memory.")

    summary = {
        "workspace": str(WORKSPACE),
        "request": "Read facts.txt once and remember the stable deploy fact.",
        "answer": answer,
        "run_dir": str(run_dir),
        "session_file": str(session_path),
        "session_events_file": str(agent.session_event_bus.path),
        "memory_dir": str(memory_root),
        "memory_state_from_agent_after_dream": agent.memory.to_dict(),
        "memory_state_from_session_file": session["memory"],
        "episodic_notes": session["memory"]["episodic_notes"],
        "file_summaries": session["memory"]["file_summaries"],
        "durable_topics": agent.memory.to_dict().get("durable_topics", []),
        "retrieval_view": agent.memory.retrieval_view("deploy key"),
        "prompt_after_contains": {
            "auto_memory_contract": "# Auto Memory" in prompt_after,
            "relevant_memory_section": "Relevant memory:" in prompt_after,
            "deploy_fact": "deploy key is red" in prompt_after,
        },
        "memory_maintenance_from_report": report["memory_maintenance"],
        "report_paths": {
            "report": str(run_dir / "report.json"),
            "trace": str(run_dir / "trace.jsonl"),
            "task_state": str(run_dir / "task_state.json"),
        },
        "trace_memory_events": [
            event
            for event in trace
            if str(event.get("event", "")).startswith("memory_")
            or event.get("event") == "tool_executed"
        ],
        "session_memory_events": [
            event
            for event in events
            if "memory" in str(event.get("event", "")) or "dream" in str(event.get("event", ""))
        ],
        "memory_files": memory_files,
    }

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "answer": answer,
        "summary": str(SUMMARY_PATH),
        "episodic_notes": len(summary["episodic_notes"]),
        "file_summaries": list(summary["file_summaries"].keys()),
        "durable_topics": summary["durable_topics"],
        "auto_dream": summary["memory_maintenance_from_report"]["auto_dream"],
    }, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
