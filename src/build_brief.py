"""검증된 공개 기사 메타데이터를 Markdown 브리핑으로 변환한다.

이 스크립트는 뉴스를 자동 수집하지 않는다. Claude Code 또는
사용자가 원문을 확인한 후 articles.json에 입력한 정보만 사용한다.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_CATEGORIES = {"시장동향", "기업이슈", "정책/규제"}
REQUIRED_ARTICLE_FIELDS = {
    "title",
    "publisher",
    "published_at",
    "url",
    "category",
    "facts",
    "interpretation",
    "check_needed",
}


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_request(request: dict) -> None:
    required = {"industry", "keywords", "date_from", "date_to", "max_articles"}
    missing = sorted(required - request.keys())
    if missing:
        raise ValueError(f"요청 파일 필수 항목 누락: {', '.join(missing)}")
    if not isinstance(request["keywords"], list) or not request["keywords"]:
        raise ValueError("keywords는 한 개 이상의 목록이어야 합니다.")
    if not isinstance(request["max_articles"], int) or request["max_articles"] < 1:
        raise ValueError("max_articles는 1 이상의 정수여야 합니다.")


def validate_article(article: dict, index: int) -> None:
    missing = sorted(REQUIRED_ARTICLE_FIELDS - article.keys())
    if missing:
        raise ValueError(f"{index}번 기사 필수 항목 누락: {', '.join(missing)}")

    parsed = urlparse(article["url"])
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{index}번 기사 URL은 유효한 https 주소여야 합니다.")

    try:
        datetime.strptime(article["published_at"], "%Y-%m-%d")
    except ValueError as error:
        raise ValueError(f"{index}번 기사 날짜는 YYYY-MM-DD 형식이어야 합니다.") from error

    if article["category"] not in ALLOWED_CATEGORIES:
        allowed = ", ".join(sorted(ALLOWED_CATEGORIES))
        raise ValueError(f"{index}번 기사 분류는 {allowed} 중 하나여야 합니다.")

    if not isinstance(article["facts"], list) or not article["facts"]:
        raise ValueError(f"{index}번 기사 facts는 한 개 이상의 목록이어야 합니다.")


def build_markdown(request: dict, articles: list[dict]) -> str:
    today = date.today().isoformat()
    industry = request["industry"]
    keywords = ", ".join(request["keywords"])
    lines = [
        f"# {today} {industry} 데일리 시장 브리핑",
        "",
        f"- 조사 키워드: {keywords}",
        f"- 조사 기간: {request['date_from']} ~ {request['date_to']}",
        f"- 검수 대상: {len(articles)}건",
        "- 상태: 사용자 원문 검수 전 초안",
        "",
        "## 1. 한눈에 보는 핵심",
        "",
    ]

    if not articles:
        lines.extend(
            [
                "입력된 검증 기사가 없습니다. 공개 원문을 확인한 후 `input/articles.json`을 채우세요.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"총 {len(articles)}건의 공개 자료가 정리되었습니다. 아래 항목의 원문과 수치를 사용자가 다시 확인해야 합니다.",
                "",
            ]
        )

    lines.extend(["## 2. 주요 뉴스", ""])
    for number, article in enumerate(articles, start=1):
        lines.extend(
            [
                f"### {number}. {article['title']}",
                "",
                f"- 분류: {article['category']}",
                f"- 발행처: {article['publisher']}",
                f"- 게시일: {article['published_at']}",
                f"- URL: {article['url']}",
                "- 확인된 사실:",
            ]
        )
        lines.extend([f"  - {fact}" for fact in article["facts"]])
        lines.extend(
            [
                f"- AI 해석: {article['interpretation']}",
                f"- 추가 확인 필요: {article['check_needed']}",
                "",
            ]
        )

    check_items = [article["check_needed"] for article in articles if article["check_needed"]]
    lines.extend(["## 3. 추가 확인 필요", ""])
    if check_items:
        lines.extend([f"- {item}" for item in check_items])
    else:
        lines.append("- 별도로 입력된 항목이 없습니다.")

    lines.extend(
        [
            "",
            "## 4. 사용자 검수 체크리스트",
            "",
            "- [ ] 모든 URL이 실제로 열리는지 확인",
            "- [ ] 기사 날짜가 조사 기간에 포함되는지 확인",
            "- [ ] 주요 수치와 인용을 원문과 대조",
            "- [ ] 사실과 AI 해석이 구분되었는지 확인",
            "- [ ] 매수·매도 단정 표현이 없는지 확인",
            "",
            "> 본 문서는 공개 정보 조사 보조용 초안으로, 투자 판단을 대신하지 않습니다.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="공개 뉴스 브리핑 초안 생성")
    parser.add_argument("--request", type=Path, default=Path("input/request.json"))
    parser.add_argument("--articles", type=Path, default=Path("input/articles.json"))
    parser.add_argument("--output", type=Path, default=Path("output/market-brief.md"))
    args = parser.parse_args()

    request = read_json(args.request)
    articles = read_json(args.articles)
    validate_request(request)
    if not isinstance(articles, list):
        raise ValueError("articles.json의 최상위 값은 목록이어야 합니다.")
    for index, article in enumerate(articles, start=1):
        validate_article(article, index)

    limited_articles = articles[: request["max_articles"]]
    markdown = build_markdown(request, limited_articles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"생성 완료: {args.output} ({len(limited_articles)}건)")


if __name__ == "__main__":
    main()
