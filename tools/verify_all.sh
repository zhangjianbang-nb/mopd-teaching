#!/usr/bin/env bash
# tools/verify_all.sh —— 一键验收（只读，不重建）。exit 0 = 全过。
set -u
cd "$(dirname "$0")/.."
RUN=$(pwd)
S=/home/whu/.zcode/skills/ai-domain-research-and-teaching/scripts
fail=0
step(){ echo; echo "===== $* ====="; }

step "1/6 站点 schema/字数/结构（verify_site --phase all）"
python3 "$S/verify_site.py" --site site --phase all || fail=1

step "2/6 可见字符账（正文口径，目标 500 万）"
python3 -I tools/ledger.py || fail=1

step "3/6 独立硬断言（75 项：字数/单件/去重/引用/故事）"
python3 -I tools/assert_all.py || fail=1

step "4/6 全页 smoke（20 条路由 + 交互 + 无外链）"
node tools/smoke.js || fail=1

step "5/6 全站图几何 + 运行时视觉断言"
python3 -I tools/fig_dump.py || fail=1
node tools/fig_probe.js shots/figtest.html || fail=1
python3 -I tools/fig_dump_all.py || fail=1
node tools/fig_probe.js shots/figtest-all.html || fail=1
node tools/visual_probe.js || fail=1

step "6/6 390px 窄屏断言"
node tools/mobile_probe.js || fail=1

echo
if [ "$fail" = 0 ]; then echo "===== 全部 PASS ====="; else echo "===== 有 FAIL ====="; fi
exit "$fail"
