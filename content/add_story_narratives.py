# -*- coding: utf-8 -*-
"""把完整故事叙事注入 stories.json 的 long_html（幂等，带标记）。

用法：python3 -I content/add_story_narratives.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
DATA = os.path.join(RUN, "site", "data")
TEXT = os.path.join(HERE, "storytext")

IDS = ["story-four-masters", "story-night-shift", "story-dispatch-table",
       "story-lift-ledger", "story-three-gates"]


def main():
    path = os.path.join(DATA, "stories.json")
    with open(path, encoding="utf-8") as f:
        stories = json.load(f)
    by_id = {s["id"]: s for s in stories}
    for sid in IDS:
        fp = os.path.join(TEXT, sid + ".html")
        with open(fp, encoding="utf-8") as f:
            text = f.read().strip()
        s = by_id[sid]
        h = s.get("long_html") or ""
        h = re.sub(r"<!--STORYTEXT:%s:start-->[\s\S]*?<!--STORYTEXT:%s:end-->" %
                   (re.escape(sid), re.escape(sid)), "", h)
        h = h.rstrip() + "\n<!--STORYTEXT:%s:start-->\n%s\n<!--STORYTEXT:%s:end-->" % (sid, text, sid)
        s["long_html"] = h
        plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()
        print("%s narrative=%d chars, long_html=%d" % (sid, len(plain), len(h)))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
