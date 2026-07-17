#!/usr/bin/env python3
"""Rewrites the LATEST and OSS marker blocks in README.md from the GitHub API."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = "aramz33"
README = Path(__file__).resolve().parent.parent / "README.md"


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def days_ago(iso):
    delta = datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return "today" if delta.days == 0 else f"{delta.days}d ago"


def latest_brick():
    for event in api(f"/users/{USER}/events/public"):
        # public events payload has no commit list anymore, only the head sha
        if event["type"] == "PushEvent" and event["payload"].get("head"):
            repo = event["repo"]["name"]
            if repo == f"{USER}/{USER}":  # skip self-referential profile-repo pushes
                continue
            msg = api(f"/repos/{repo}/commits/{event['payload']['head']}")["commit"]["message"].splitlines()[0]
            return (
                f'latest brick: [{repo}](https://github.com/{repo}) — '
                f'"{msg}" ({days_ago(event["created_at"])})'
            )
    return ""


def oss_prs():
    # is:public keeps employer/private-org PRs out of the public README
    items = api(f"/search/issues?q=is:pr+is:public+author:{USER}+-user:{USER}&sort=created&order=desc")["items"]
    lines = []
    for pr in items[:10]:
        # repository_url = https://api.github.com/repos/owner/repo
        repo = "/".join(pr["repository_url"].split("/")[-2:])
        merged = pr.get("pull_request", {}).get("merged_at")
        state = "merged" if merged else ("open" if pr["state"] == "open" else "closed")
        lines.append(f'- [{repo}#{pr["number"]}]({pr["html_url"]}) — {state} · {pr["title"]}')
    return "\n".join(lines)


def replace_block(text, name, content):
    return re.sub(
        f"<!-- {name}:START -->.*<!-- {name}:END -->",
        f"<!-- {name}:START -->\n{content}\n<!-- {name}:END -->",
        text,
        flags=re.DOTALL,
    )


def main():
    old = README.read_text()
    new = replace_block(old, "LATEST", latest_brick())
    new = replace_block(new, "OSS", oss_prs())
    if new != old:
        README.write_text(new)
        print("README updated")
    else:
        print("no changes")


if __name__ == "__main__":
    main()
