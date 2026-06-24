# Trace Tracking Memory Run

本目录是一轮典型文件访问的实际运行产物，重点看：

- `episodic_notes`
- `file_summaries`
- `durable_topics`
- auto-dream 触发、写入位置和 trace/report 记录

没有运行 memory ablation。

## 复跑命令

在项目根目录执行：

```bash
python memory-test/trace-tracking/run_trace_tracking.py
```

脚本会重建：

```text
memory-test/trace-tracking/demo-workspace/
```

并把该目录初始化为独立 git repo，避免 Pico 的 auto-dream 向上找到项目根目录。

## 本次访问链路

输入文件：

```text
demo-workspace/facts.txt
```

内容：

```text
alpha
deploy key is red
memory demos should be deterministic
```

主 agent 第一轮动作：

1. `read_file facts.txt`
2. final answer: `Read facts. <memory>Project: deploy key is red.</memory>`

这一步产生：

- `file_summaries["facts.txt"]`
- 一条 `episodic_notes`
- daily log: `.pico/memory/logs/2026/06/2026-06-24.md`
- auto-dream 触发

auto-dream 子 agent 动作：

1. 读取 memory index
2. 写 `.pico/memory/topics/project.md`
3. 写 `.pico/memory/MEMORY.md`
4. final: `Dream consolidated project memory.`

## 关键文件

| 文件 | 说明 |
| --- | --- |
| `run_trace_tracking.py` | 本次实验脚本。 |
| `trace-tracking-summary.json` | 聚合摘要，直接摘出 `episodic_notes`、`file_summaries`、`durable_topics`、auto-dream 事件。 |
| `demo-workspace/.pico/sessions/20260624-154304-612f93.json` | 主 agent session，里面有主 session 的 memory state。 |
| `demo-workspace/.pico/runs/run_20260624-154304-64b87d/report.json` | 主 agent run report，里面有 `memory_maintenance`。 |
| `demo-workspace/.pico/runs/run_20260624-154304-64b87d/trace.jsonl` | 主 agent trace，里面有 `tool_executed`、`memory_auto_dream_started`、`memory_auto_dream_finished`。 |
| `demo-workspace/.pico/memory/logs/2026/06/2026-06-24.md` | `<memory>Project: deploy key is red.</memory>` 写入的 daily log。 |
| `demo-workspace/.pico/memory/MEMORY.md` | auto-dream 更新的 durable memory index。 |
| `demo-workspace/.pico/memory/topics/project.md` | auto-dream 写出的 durable topic。 |
| `demo-workspace/.pico/sessions/20260624-154305-ab35ef.json` | auto-dream 子 agent 的 session。 |
| `demo-workspace/.pico/runs/run_20260624-154305-4d8065/report.json` | auto-dream 子 agent 的 run report。 |

## episodic_notes

来自 `trace-tracking-summary.json`：

```json
[
  {
    "kind": "episodic",
    "source": "facts.txt",
    "tags": ["facts.txt"],
    "text": "1: alpha | 2: deploy key is red | 3: memory demos should be deterministic"
  }
]
```

含义：`read_file facts.txt` 后，runtime 把文件读取结果压缩成一条 session 内短笔记。

## file_summaries

来自 `trace-tracking-summary.json`：

```json
{
  "facts.txt": {
    "summary": "1: alpha | 2: deploy key is red | 3: memory demos should be deterministic",
    "freshness": "64e21720be291631ed252f03c80608b78f2b8dbf2010cb74000148801b437d86"
  }
}
```

含义：`file_summaries` 记录文件短摘要，同时带文件 hash。文件内容变化后，旧摘要会失效。

## durable_topics

来自 `trace-tracking-summary.json`：

```json
["Project Memory"]
```

对应文件：

```text
demo-workspace/.pico/memory/MEMORY.md
demo-workspace/.pico/memory/topics/project.md
```

`MEMORY.md` 是索引，`topics/project.md` 是长期记忆正文。

## auto-dream

来自主 run report 的 `memory_maintenance.auto_dream`：

```json
{
  "enabled": true,
  "triggered": true,
  "status": "finished",
  "session_count": 2,
  "session_ids": ["older-0", "older-1"],
  "changed_files": [
    ".pico/memory/MEMORY.md",
    ".pico/memory/topics/project.md"
  ]
}
```

含义：

- `triggered=true`：达到 session gate，auto-dream 被触发。
- `status=finished`：后台 dream 子 agent 成功完成。
- `changed_files`：auto-dream 实际改了 memory index 和 topic 文件。

trace 中可查：

- `memory_auto_dream_started`
- `memory_auto_dream_finished`

session events 中可查：

- `memory_note_appended`
- `auto_dream_started`
- `dream_consolidated`
