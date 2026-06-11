#!/usr/bin/env python3
"""content/ 디렉토리의 글 구조를 검증한다.

CONTRIBUTING.md의 규칙을 그대로 자동화한다.
  - 한 글 = 폴더 하나 + 그 안의 index.md (본문은 반드시 index.md)
  - 슬러그(글 폴더명)는 kebab-case
  - 글은 아래에 정의된 '알려진 카테고리' 바로 밑에만 둔다 (임의 카테고리 폴더 금지)

카테고리 트리는 CONTRIBUTING.md의 '카테고리' 섹션과 짝이다.
새 카테고리를 합의해 추가할 때는 두 곳을 함께 고친다.
"""

import re
import sys
from pathlib import Path

# content/ 기준 상대 경로로 표현한 알려진 카테고리.
# 글은 이 경로들 중 하나 바로 아래에 (한 폴더 깊이로) 들어간다.
KNOWN_CATEGORIES = {
    "data-structure",
    "graph",
    "graph/tree",
    "graph/shortest-path",
    "graph/mst",
    "graph/scc",
    "graph/network-flow",
    "dp",
    "dp/optimization",
    "string",
    "math",
    "math/number-theory",
    "math/combinatorics",
    "math/linear-algebra",
    "math/polynomial",
    "geometry",
    "technique",
    "greedy",
    "game-theory",
}

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

CONTENT = Path("content")


def main() -> int:
    if not CONTENT.is_dir():
        print("content/ 디렉토리가 없습니다.")
        return 1

    errors: list[str] = []

    # 1) content/ 아래의 모든 마크다운은 index.md 여야 한다.
    #    (한 글 = 폴더 + index.md 규칙. dijkstra.md 같은 평면 파일 금지)
    for md in CONTENT.rglob("*.md"):
        if md.name != "index.md":
            errors.append(
                f"{md.as_posix()}: 본문 파일명은 index.md 여야 합니다. "
                f"(글은 '폴더 + index.md' 구조)"
            )

    # 2) 각 index.md = 한 편의 글. 그 폴더의 위치/이름을 검증한다.
    for index in CONTENT.rglob("index.md"):
        folder = index.parent
        rel = folder.relative_to(CONTENT)  # 예: graph/shortest-path/dijkstra
        parts = rel.parts

        if not parts:
            errors.append(
                "content/index.md: 글은 카테고리 폴더 아래에 두어야 합니다. "
                "content/ 루트에 직접 둘 수 없습니다."
            )
            continue

        slug = parts[-1]
        category = "/".join(parts[:-1])

        if category not in KNOWN_CATEGORIES:
            shown = category if category else "(루트)"
            errors.append(
                f"{folder.as_posix()}: '{shown}'은(는) 알려진 카테고리가 아닙니다. "
                f"새 카테고리는 PR에서 임의 생성하지 말고 Issue로 먼저 제안해 주세요."
            )

        if not SLUG_RE.match(slug):
            errors.append(
                f"{folder.as_posix()}: 슬러그 '{slug}'가 kebab-case가 아닙니다. "
                f"(소문자/숫자/하이픈만, 예: binary-search)"
            )

    # 3) 에셋(이미지 등)만 있고 index.md가 없는 '유령 글 폴더'를 잡는다.
    #    글 = 폴더 + index.md 이므로, 본문 없이 에셋만 들어온 폴더는 실수다.
    #    (하위 폴더만 가진 카테고리 폴더, .gitkeep만 있는 폴더는 대상이 아니다)
    #    .gitkeep·.DS_Store 등 점(.)으로 시작하는 파일은 OS/도구 부산물이며
    #    글 에셋이 아니므로 제외한다.
    asset_folders = {
        f.parent
        for f in CONTENT.rglob("*")
        if f.is_file() and not f.name.startswith(".") and f.suffix != ".md"
    }
    for folder in asset_folders:
        if not (folder / "index.md").exists():
            errors.append(
                f"{folder.as_posix()}: 에셋만 있고 index.md가 없습니다. "
                f"(글 본문 index.md와 같은 폴더에 두어야 합니다)"
            )

    if errors:
        print("✗ 구조 검증 실패:\n")
        for e in errors:
            print(f"  - {e}")
        print(f"\n총 {len(errors)}건. CONTRIBUTING.md의 '글 작성 규칙'을 확인해 주세요.")
        return 1

    print("✓ 구조 검증 통과.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
