"""Read-only format audit of public CN GitHub/torappu collectible resources.

No Wiki client, login, or write API is imported. Downloads are saved for offline
reproduction; report.json records pinned GitHub commits and torappu resVersion.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ptilopsis.relics.source import (
    RelicGlossary,
    RelicTopics,
    build_records,
    render_pages,
)


def get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Ptilopsis-relic-format-audit/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def analyze(topic_raw: dict, const_raw: dict) -> dict:
    topics = RelicTopics.model_validate(topic_raw)
    glossary = RelicGlossary.model_validate(const_raw)
    records = build_records(topics, glossary)
    pages = render_pages(records)
    return {
        "topics_format": type(topic_raw["topics"]).__name__,
        "details_format": type(topic_raw["details"]).__name__,
        "themes": {key: value.name for key, value in topics.topics.items()},
        "relic_pages": len(pages),
        "relic_items": sum(
            sum(item.type == "RELIC" for item in detail.items.values())
            for detail in topics.details.values()
        ),
        "rendered_sha256": hashlib.sha256(
            json.dumps(
                {page["title"]: page["text"] for page in pages},
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        "compatible": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    files = ["roguelike_topic_table.json", "gamedata_const.json"]
    report = {"sources": {}}
    if args.offline:
        report = json.loads((args.output / "report.json").read_text(encoding="utf-8"))
        report["sources"] = {
            name: entry
            for name, entry in report["sources"].items()
            if name in {"github-cn", "torappu-cn"}
        }
        for name, entry in report["sources"].items():
            if not all((args.output / name / filename).is_file() for filename in files):
                continue
            try:
                entry["validation"] = analyze(
                    *[
                        json.loads((args.output / name / filename).read_bytes())
                        for filename in files
                    ]
                )
            except (ValueError, KeyError, TypeError) as exc:
                entry["validation"] = {"compatible": False, "error": str(exc)[:3000]}
    else:
        for name, repo, folder in [
            ("github-cn", "Kengxxiao/ArknightsGameData", "zh_CN"),
            ("torappu-cn", None, None),
        ]:
            entry = report["sources"][name] = {}
            try:
                if repo:
                    commit = json.loads(
                        get(f"https://api.github.com/repos/{repo}/commits/HEAD")
                    )
                    entry.update(
                        commit=commit["sha"],
                        commit_date=commit["commit"]["committer"]["date"],
                    )
                    base = f"https://raw.githubusercontent.com/{repo}/{commit['sha']}/{folder}/gamedata/excel"
                else:
                    base_url = "https://torappu.prts.wiki"
                    versions = sorted(
                        json.loads(get(base_url + "/api/v1/version")),
                        key=lambda value: value["id"],
                        reverse=True,
                    )
                    for version in versions[:10]:
                        if not version["isReady"]:
                            continue
                        base = f"{base_url}/gamedata/{version['resVersion']}"
                        try:
                            get(base + "/.gamedata-ready.json")
                        except HTTPError as exc:
                            if exc.code == 404:
                                continue
                            raise
                        entry.update(
                            res_version=version["resVersion"],
                            client_version=version["clientVersion"],
                        )
                        base += "/excel"
                        break
                    else:
                        raise ValueError(
                            "No ready torappu version in latest ten candidates"
                        )
                data = []
                entry["files"] = []
                directory = args.output / name
                directory.mkdir(exist_ok=True)
                for filename in files:
                    url = base + "/" + filename
                    content = get(url)
                    (directory / filename).write_bytes(content)
                    entry["files"].append(
                        {
                            "url": url,
                            "bytes": len(content),
                            "sha256": hashlib.sha256(content).hexdigest(),
                        }
                    )
                    data.append(json.loads(content))
                try:
                    entry["validation"] = analyze(*data)
                except (ValueError, KeyError, TypeError) as exc:
                    entry["validation"] = {
                        "compatible": False,
                        "error": str(exc)[:3000],
                    }
            except Exception as exc:
                entry["fetch_error"] = f"{type(exc).__name__}: {exc}"
    (args.output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name, entry in report["sources"].items():
        summary = {key: value for key, value in entry.items() if key != "files"}
        print(name, json.dumps(summary, ensure_ascii=False))  # noqa: T201
    if not all(
        report["sources"].get(name, {}).get("validation", {}).get("compatible")
        for name in ("github-cn", "torappu-cn")
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
