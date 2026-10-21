# control-list-check

Kortix is open source. The open-source AI Operating System is how Kortix describes itself: agents, skills, company memory and connectors in one git repo you own, with a cloud computer per session.

A vendor sends you a security-control grid. Every cell is a tick, and nothing behind the tick can be checked. This is a small script that changes that: put one sentence from the vendor's own page in each row, next to the URL it came from, and the script tells you when that sentence is gone.

It runs on any vendor, not just the one in `examples/`. One command, no account, no dependency beyond `uv`.

```sh
git clone https://github.com/ArtemShatokhin/control-list-check
cd control-list-check
uv run control_list_check.py examples/chatgpt-work.yaml
```

```
held       Cloud execution -> https://learn.chatgpt.com/docs/enterprise/chatgpt-work-overview
held       Approval before an action -> https://learn.chatgpt.com/docs/enterprise/chatgpt-work-overview
...
{"held": 10}
```

## Why a sentence and not a tick

A tick-box grid is a claim about a product with no evidence attached. A sentence copied from the vendor's page is evidence with a URL, and it has one property a tick does not: it can stop being true, and you can find out. When a vendor renames a control, narrows a limit or drops a claim, the sentence changes and the check fails on that row alone. The row then names the page to re-read.

The same reasoning decides what belongs in your own stack: a control you cannot point at a page for is a control you cannot put in a review. [How a stack you own answers the ChatGPT Work control set](https://chatgptworkalternative.com) is one worked example, and [the method, walked through](https://kortix.com/blog/chatgpt-work-enterprise-controls-recheck) is the longer version.

## The rows file

```yaml
checked: 2026-10-21          # the date a person last looked at the grid
sources:
  docs: https://vendor.example/security
rows:
  - control: Single sign-on
    source: docs             # a key in sources, or a full URL
    quote: "SAML 2.0 single sign-on"
    ours: What your own stack does instead
  - control: Pen-test summary
    source: docs
    manual: true             # a script cannot read this page; a person must
    quote: "available on request"
```

- `quote` is the vendor's own sentence. Copy it from the page; never paraphrase, or the check compares your words with theirs and fails.
- `manual: true` is for a page that refuses a script or a control that lives only in a document a person reads. It is counted separately, never silently passed.
- `ours` is optional and free text. The script never checks it, because it is your claim, not the vendor's.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Every non-manual quote was found on its page. |
| 1 | At least one quote is gone. Copy the new sentence from the page, keep the URL, update `checked`. |
| 2 | No quote was missing, but a page could not be read: 403, 404, a timeout, a network error. |

`--json` prints the whole report with one object per row (`held`, `missing`, `unreadable`, `manual`, `no-quote`, `no-source`). `--quiet` prints nothing and keeps the exit code, which is what a cron job wants.

Add a scheduled job to run it weekly. A control that silently changes then becomes a failed run instead of a stale tick:

```yaml
# .github/workflows/check.yml
on:
  schedule: [{cron: "0 6 * * 1"}]
  workflow_dispatch:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv run control_list_check.py examples/chatgpt-work.yaml
```

## Limits worth knowing before you rely on it

- It compares text, so a page that renders its sentences in JavaScript or behind a login reads as unreadable. That is the honest answer, not a bug.
- A vendor can keep a sentence and change the behaviour behind it. A quote proves what was published, never what the product does.
- A sentence that appears elsewhere on the page still counts as held. Point `source` at the narrowest page you have: a per-feature docs page, not a marketing home page.

The example rows are ChatGPT Work's documented enterprise controls, read on 2026-10-21, each with the sentence OpenAI's own page uses. Ten of ten were still there on that date, which is what a passing run looks like.
