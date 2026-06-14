#!/usr/bin/env python3
"""content/ 디렉토리의 글 구조를 검증한다.

CONTRIBUTING.md의 규칙을 그대로 자동화한다.
  - 한 글 = 카테고리 폴더 아래의 평면 마크다운 파일 <슬러그>.md
    (예: content/dp/knapsack/dijkstra.md). 폴더+index.md 구조가 아니다.
  - 글에 이미지 등 에셋이 있으면 글과 같은 이름의 폴더(<슬러그>/)에 둔다.
    (예: dijkstra.md 옆에 dijkstra/ 폴더, 그 안에 그림). 그 폴더엔 .md를 두지 않는다.
  - 슬러그(글 파일명 / 에셋 폴더명)는 kebab-case
  - 글은 아래에 정의된 '알려진 카테고리' 바로 밑에만 둔다 (임의 카테고리 폴더 금지)
  - 단, content/index.md(루트)는 사이트 홈페이지라 글 규칙에서 면제한다
  - content/stylesheets/ 등 예약 디렉토리(RESERVED_DIRS)는 사이트 에셋이라 면제한다
  - .nav.yml 등 점(.)으로 시작하는 파일은 도구 설정/부산물이라 글 검사 대상이 아니다

카테고리 트리는 CONTRIBUTING.md의 '카테고리' 섹션과 짝이다.
새 카테고리를 합의해 추가할 때는 두 곳을 함께 고친다.
"""

import re
import sys
from pathlib import Path

# content/ 기준 상대 경로로 표현한 알려진 카테고리.
# 글(<슬러그>.md)은 이 경로들 중 하나 바로 아래에 들어간다.
KNOWN_CATEGORIES = {
    "data-structure",
    "sorting",
    "graph",
    "graph/tree",
    "graph/shortest-path",
    "graph/mst",
    "graph/scc",
    "graph/network-flow",
    "dp",
    "dp/knapsack",
    "dp/lcs",
    "dp/lis",
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
# (MkDocs extra_css 경로가 docs_dir=content 기준이라 브랜드 CSS를 여기 둔다.)
RESERVED_DIRS = {"stylesheets"}

CONTENT = Path("content")


def parse_frontmatter(text: str) -> dict | None:
    """글 맨 위의 YAML frontmatter를 최소 파싱한다.

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
            value = m.group(2).strip()
            # YAML 표준 따옴표를 허용한다(id: "foo" / title: '...' 같은 값도 받아들임).
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[m.group(1)] = value
    return None  # 닫는 '---' 가 없다


def main() -> int:
    if not CONTENT.is_dir():
        print("content/ 디렉토리가 없습니다.")
        return 1

    errors: list[str] = []
    seen_ids: dict[str, str] = {}     # id -> 그 id를 처음 쓴 글 경로 (유일성 검사용)
    asset_dirs: set[str] = set()      # 글 에셋 폴더 경로(카테고리/슬러그) 모음

    # 1) 각 글 = 카테고리 폴더 아래의 평면 <슬러그>.md.
    #    위치(카테고리)·이름(슬러그)·frontmatter(id·title)를 검증한다.
    for md in CONTENT.rglob("*.md"):
        rel = md.relative_to(CONTENT)

        if rel.as_posix() == "index.md":
            # content/index.md = 사이트 홈페이지(SSG 랜딩). 글이 아니므로 면제한다.
            continue

        if md.name == "index.md":
            # 옛 구조(폴더+index.md) 잔재를 명확히 안내한다.
            errors.append(
                f"{md.as_posix()}: 글은 폴더+index.md가 아니라 카테고리 아래 "
                f"<슬러그>.md 평면 파일로 둡니다. (예: dp/knapsack/dijkstra.md)"
            )
            continue

        # 에셋 폴더(<슬러그>/) 안에는 글을 둘 수 없다. 부모 폴더와 같은 이름의
        # <부모>.md 가 형제로 있으면 그 부모 폴더는 글의 에셋 폴더다.
        parent = md.parent
        if parent != CONTENT and (parent.parent / (parent.name + ".md")).exists():
            errors.append(
                f"{md.as_posix()}: 에셋 폴더 '{parent.name}/' 안에는 글(.md)을 둘 수 없습니다. "
                f"글은 카테고리 폴더 바로 아래 <슬러그>.md로 두고, 그 폴더엔 이미지 등 에셋만 둡니다."
            )
            continue

        category = rel.parent.as_posix()  # 예: dp/knapsack
        slug = md.stem                    # 예: dijkstra

        # 슬러그가 알려진 카테고리 경로와 겹치면 카테고리 폴더와 글이 경로 충돌해
        # 폴더 검증이 우회된다. 명시적으로 거부한다.
        article_path = f"{category}/{slug}" if category else slug
        if article_path in KNOWN_CATEGORIES:
            errors.append(
                f"{md.as_posix()}: 슬러그 '{slug}'가 카테고리 경로 '{article_path}'와 겹칩니다. "
                f"글 슬러그는 카테고리명과 같게 지을 수 없습니다."
            )

        if category not in KNOWN_CATEGORIES:
            shown = category if category else "(루트)"
            errors.append(
                f"{md.as_posix()}: '{shown}'은(는) 알려진 카테고리가 아닙니다. "
                f"글은 알려진 카테고리 폴더 바로 아래에 두고, 새 카테고리는 "
                f"PR에서 임의 생성하지 말고 Issue로 먼저 제안해 주세요."
            )

        if not SLUG_RE.match(slug):
            errors.append(
                f"{md.as_posix()}: 슬러그 '{slug}'가 kebab-case가 아닙니다. "
                f"(소문자/숫자/하이픈만, 예: binary-search)"
            )

        # 이 글이 에셋 폴더(<슬러그>/)를 가질 수 있으므로 경로를 기록해 둔다.
        asset_dirs.add(f"{category}/{slug}" if category else slug)

        # frontmatter(id·title) 검증. id는 본 서비스가 글을 참조하는 불변 키이므로
        # 유일·kebab-case를 강제한다.
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(
                f"{md.as_posix()}: 맨 위에 frontmatter가 없습니다. "
                f"글은 '---'로 감싼 id·title로 시작해야 합니다."
            )
            continue

        if not fm.get("title"):
            errors.append(f"{md.as_posix()}: frontmatter에 title이 없습니다.")

        gid = fm.get("id", "")
        if not gid:
            errors.append(f"{md.as_posix()}: frontmatter에 id가 없습니다.")
        elif not SLUG_RE.match(gid):
            errors.append(
                f"{md.as_posix()}: id '{gid}'가 kebab-case가 아닙니다. "
                f"(소문자/숫자/하이픈만)"
            )
        elif gid in seen_ids:
            errors.append(
                f"{md.as_posix()}: id '{gid}'가 이미 {seen_ids[gid]}에서 "
                f"쓰였습니다. id는 저장소 전체에서 유일해야 합니다."
            )
        else:
            seen_ids[gid] = md.as_posix()

    # 2) content/ 아래 모든 디렉토리는 셋 중 하나여야 한다:
    #    (a) 알려진 카테고리, (b) 글 에셋 폴더(<슬러그>/, 형제 <슬러그>.md 존재)이거나 그 하위,
    #    (c) 예약 디렉토리(stylesheets 등).
    #    그 외는 임의 카테고리 폴더이거나 짝 없는 고아 에셋 폴더라 실수다.
    for d in CONTENT.rglob("*"):
        if not d.is_dir():
            continue
        rel = d.relative_to(CONTENT)
        relposix = rel.as_posix()

        if rel.parts and rel.parts[0] in RESERVED_DIRS:
            continue
        if relposix in KNOWN_CATEGORIES:
            continue
        # 에셋 폴더이거나 그 하위인가
        if any(relposix == a or relposix.startswith(a + "/") for a in asset_dirs):
            continue

        errors.append(
            f"{d.as_posix()}: 알 수 없는 폴더입니다. 카테고리는 Issue로 먼저 제안하고, "
            f"글 에셋은 글과 같은 이름의 폴더(<슬러그>.md 옆 <슬러그>/)에 두어야 합니다."
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
