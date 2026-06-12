#!/usr/bin/env python3
"""content/ 디렉토리의 글 구조를 검증한다.

CONTRIBUTING.md의 규칙을 그대로 자동화한다.
  - 한 글 = 폴더 하나 + 그 안의 index.md (본문은 반드시 index.md)
  - 슬러그(글 폴더명)는 kebab-case
  - 글은 아래에 정의된 '알려진 카테고리' 바로 밑에만 둔다 (임의 카테고리 폴더 금지)
  - 단, content/index.md(루트)는 사이트 홈페이지라 글 규칙에서 면제한다
  - content/stylesheets/ 등 예약 디렉토리(RESERVED_DIRS)는 사이트 에셋이라 면제한다

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

# content/ 아래에서 '글'이 아니라 사이트 에셋을 담는 예약 디렉토리.
# 여기 파일은 글 구조 검사(폴더+index.md 규칙)에서 면제한다.
# (MkDocs extra_css 경로가 docs_dir=content 기준이라 브랜드 CSS를 여기 둔다.)
RESERVED_DIRS = {"stylesheets"}

CONTENT = Path("content")


def parse_frontmatter(text: str) -> dict | None:
    """index.md 맨 위의 YAML frontmatter를 최소 파싱한다.

    외부 의존성(PyYAML) 없이 '키: 값' 한 줄 형태만 읽는다.
    우리 frontmatter는 id·title 정도로 단순해 이 정도면 충분하다.
    맨 위가 '---'로 시작하지 않거나 닫는 '---'가 없으면 None을 반환한다.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        m = re.match(r"^([A-Za-z][A-Za-z0-9_]*):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return None  # 닫는 '---' 가 없다


def main() -> int:
    if not CONTENT.is_dir():
        print("content/ 디렉토리가 없습니다.")
        return 1

    errors: list[str] = []
    seen_ids: dict[str, str] = {}  # id -> 그 id를 처음 쓴 글 경로 (유일성 검사용)

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
            # content/index.md = 사이트 홈페이지(SSG 랜딩). 글이 아니므로
            # 카테고리·슬러그·frontmatter id 규칙에서 면제한다.
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

        # 2-1) frontmatter(id·title)를 검증한다.
        #      id는 본 서비스가 글을 참조하는 불변 키이므로 유일·kebab-case를 강제한다.
        fm = parse_frontmatter(index.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(
                f"{index.as_posix()}: 맨 위에 frontmatter가 없습니다. "
                f"index.md는 '---'로 감싼 id·title로 시작해야 합니다."
            )
            continue

        if not fm.get("title"):
            errors.append(f"{index.as_posix()}: frontmatter에 title이 없습니다.")

        gid = fm.get("id", "")
        if not gid:
            errors.append(f"{index.as_posix()}: frontmatter에 id가 없습니다.")
        elif not SLUG_RE.match(gid):
            errors.append(
                f"{index.as_posix()}: id '{gid}'가 kebab-case가 아닙니다. "
                f"(소문자/숫자/하이픈만)"
            )
        elif gid in seen_ids:
            errors.append(
                f"{index.as_posix()}: id '{gid}'가 이미 {seen_ids[gid]}에서 "
                f"쓰였습니다. id는 저장소 전체에서 유일해야 합니다."
            )
        else:
            seen_ids[gid] = index.as_posix()

    # 3) 에셋(이미지 등)만 있고 index.md가 없는 '유령 글 폴더'를 잡는다.
    #    글 = 폴더 + index.md 이므로, 본문 없이 에셋만 들어온 폴더는 실수다.
    #    (하위 폴더만 가진 카테고리 폴더, .gitkeep만 있는 폴더는 대상이 아니다)
    #    .gitkeep·.DS_Store 등 점(.)으로 시작하는 파일은 OS/도구 부산물이며
    #    글 에셋이 아니므로 제외한다.
    asset_folders = {
        f.parent
        for f in CONTENT.rglob("*")
        if f.is_file()
        and not f.name.startswith(".")
        and f.suffix != ".md"
        and f.relative_to(CONTENT).parts[0] not in RESERVED_DIRS
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
