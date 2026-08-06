# -*- coding: utf-8 -*-
"""earnings_briefs.json 安全追加工具 — 固化 8/4 教训（禁止整文件重写）+ 7/21 教训（防重复 key）。

用法：
  python3 add_brief.py new_briefs.json        # 从文件读新条目并追加
  python3 add_brief.py -                      # 从 stdin 读 JSON

输入格式（与 earnings_briefs.json 条目一致）：
  {"CSCO_2026-08-12": {"summary_cn": "...", "thesis_cn": "...", "researched_at": "...", "version": 1}, ...}

行为：
  - 纯文本级追加（插入到文件末尾闭合大括号之前），不重排、不改缩进，git diff 只有新增行
  - key 已存在则拒绝该条并列出（不覆盖；如需更新请手动 Edit 原条目）
  - 追加后校验：json 可解析、条目数 = 原数 + 新增数、每个新 key 文本层面恰好出现 1 次
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(REPO, "earnings_briefs.json")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    src = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8").read()
    new_entries = json.loads(src)
    assert isinstance(new_entries, dict) and new_entries, "输入必须是非空 dict"

    text = open(TARGET, encoding="utf-8").read()
    before = json.loads(text)

    dup = [k for k in new_entries if k in before]
    if dup:
        print(f"[SKIP] 已存在的 key（不覆盖）：{dup}")
    todo = {k: v for k, v in new_entries.items() if k not in before}
    if not todo:
        print("没有可新增的条目，退出。")
        return

    parts = []
    for k, v in todo.items():
        body = json.dumps(v, ensure_ascii=False, indent=2)
        lines = body.split("\n")
        # 对齐现有风格：key 1 空格缩进、字段 2 空格缩进
        shifted = [' "%s": {' % k] + [" " + ln for ln in lines[1:-1]] + [" }"]
        parts.append("\n".join(shifted))

    stripped = text.rstrip()
    idx = stripped.rfind("\n}")
    assert idx > 0, "目标文件结构异常（找不到结尾闭合大括号）"
    new_text = stripped[:idx].rstrip() + ",\n" + ",\n".join(parts) + "\n}\n"

    after = json.loads(new_text)
    assert len(after) == len(before) + len(todo), "条目数校验失败"
    for k in todo:
        cnt = new_text.count(f'"{k}"')
        assert cnt == 1, f"key {k} 文本层面出现 {cnt} 次（应为 1）"

    open(TARGET, "w", encoding="utf-8").write(new_text)
    print(f"OK：新增 {len(todo)} 条（{list(todo)}），总条目 {len(after)}")


if __name__ == "__main__":
    main()
