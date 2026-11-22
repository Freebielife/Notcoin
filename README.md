# Notcoin Observatory

Standalone, bilingual (RU/EN) TON token observatory, generated from the vetted
[Freebielife/Ludoman factory](https://github.com/Freebielife/Ludoman/blob/main/docs/NEW_PROJECT_FACTORY.md).
It is an independent community analytics site, not an official Notcoin service.

## Verified project identity

- NOT jetton master: `EQAvlWFDxGF2lXm67y4yzC17wYKD9A0guwPkMs1gOsM__NOT`
- Decimals: 9
- STON.fi NOT/TON pool: `EQCaY8Ifl2S6lRBMBJeY35LIuMXPc8JfItWG4tl7lBGrSoR2`
- DeDust NOT/TON pool: `EQCUhnOllvxtLDEj3_9k0yMeTQ4Wv6rFBtXr2wnzKzucZeER`
- Official channel supplied by the owner: https://t.me/notcoin
- Project home: https://notcoin.org/
- Official X: https://x.com/notcoin

Pool sources:
- https://www.geckoterminal.com/ton/pools/EQCaY8Ifl2S6lRBMBJeY35LIuMXPc8JfItWG4tl7lBGrSoR2
- https://www.geckoterminal.com/ton/pools/EQCUhnOllvxtLDEj3_9k0yMeTQ4Wv6rFBtXr2wnzKzucZeER

## Files and operations

- `index.html`: standalone responsive page, no CDN-based frontend runtime.
- `data/snapshot.json`: embedded source data and remote refresh snapshot.
- `project.json`: token, source pools, socials and project-specific settings.
- `.github/workflows/update.yml`: receives workflow_dispatch and rebuilds
  the snapshot; source collection saves verified sections and preserves errors.
- `.github/workflows/visual-qa.yml`: browser checks, screenshots for
  360 / 390 / 768 / 1280 px, bilingual controls, links and overflow.
- `qa/browser_qa.py`: smoke tests for the standalone page.

The historical market-cap series is inferred from on-chain DEX prices and
the **current** supply; it is an estimate, not the historical circulating
supply. The backfill adds older verified swaps incrementally. Top holder
rankings display a sampled top 100; the total holder count is sourced
separately. Service wallet labels are attributed, not inferred from size.

## To enable unattended external refreshes

The shared runner lives in `Freebielife/Ludoman/cloudflare/observatory-runner`.
Notcoin has been added there with `enabled: false` to avoid unauthorized
dispatches. Before changing it to `true`:

1. Make this repository public if the TON site should load fresh JSON directly
   from the GitHub raw/contents endpoints. Otherwise a separately authorized
   public snapshot endpoint is required.
2. Grant the **existing** fine-grained GitHub token used by the Cloudflare
   Observatory Runner access to the `Freebielife/Notcoin` repository with
   **Actions: Read and write**. Do **not** paste this token into chats or files.
3. Enable the project in `cloudflare/observatory-runner/src/projects.mjs`,
   deploy the change, and confirm at least two real `workflow_dispatch` runs.
   The staged cadence is 30 minutes, phase :20 / :50 UTC.

Publishing `index.html` to TON Sites / TON Storage is a separate step,
not performed by GitHub Actions. Until the new repo is public, the standalone
HTML shows its embedded snapshot but cannot fetch new data anonymously from
a private GitHub repository.

## Run locally

```bash
python3 -m scripts.refresh_observatory
python3 build.py
python3 verify.py
python3 -m unittest discover -s tests -p 'test_*.py'
node --check web/app.js
node --test tests/*.test.cjs
```
