# 版本規則 / 版本规则 / Version policy

v1.0.0 is the earliest TTermite baseline, with a complete trilingual capability overview. Original development history is preserved. Later releases each contain one independently tracked change and one reachable commit.

| 類別 / 类别 / Category | 增版 / Increment | Example |
| --- | --- | --- |
| 新增 / 新增 / Added | minor + 1, patch = 0 | 1.0.2 → 1.1.0 |
| 刪除 / 删除 / Removed | minor + 1, patch = 0 | 1.1.3 → 1.2.0 |
| 修正、優化 / 修正、优化 / Improved | patch + 1 | 1.1.0 → 1.1.1 |
| 其它 / 其它 / Other | patch + 1 | 1.1.1 → 1.1.2 |
| 大幅改變架構的重大新增 / 大幅改变架构的重大新增 / Major architectural addition | major + 1, minor = patch = 0 | 1.8.4 → 2.0.0 |

Each build number increases. Major changes require a concrete architectureRationale. Fixes use the Improved category. Supply exactly one change object and an ordered noteCategories list; all three languages must match in count, order, category and meaning. Explain each change, its observable effect and material limitations together.

Copy docs/release-notes-template.json to ignored build/next-release-notes.json, fill the change ID/category and all notes, then run `python3 scripts/prepare-version.py --notes build/next-release-notes.json`. The tool derives the version; an explicit --version must agree. Review source isolation and test/build the exact committed revision independently. Metadata checks cannot prove that two unrelated changes were not bundled.

Source candidates and planned changes are not delivered releases. Local verification data stays in ignored build directories; publish only independently tested sources. Do not relabel binaries, move remote tags or rewrite original development commits.
