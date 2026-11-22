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
- Main logo: `web/project-logo.webp`, rasterized locally from the rounded SVG
  linked on the [Notcoin project website](https://notcoin.org/):
  `https://cdn.joincommunity.xyz/explore/icons/notcoin-logo-rounded.svg`.
  The provenance and conversion are recorded in `.github/workflows/brand-logo.yml`.
- Compact NOT token marker: `web/flag-notcoin-036.webp`, extracted from the
  owner's **TONecoFlags #036** catalog. This is a separate community flag,
  shown only beside NOT labels in pools and transaction rows.
- Both files are embedded directly into `index.html` by `build.py`.
  There are no runtime image CDNs or image requests.

Pool sources:
- https://www.geckoterminal.com/ton/pools/EQCaY8Ifl2S6lRBMBJeY35LIuMXPc8JfItWG4tl7lBGrSoR2
- https://www.geckoterminal.com/ton/pools/EQCUhnOllvxtLDEj3_9k0yMeTQ4Wv6rFBtXr2wnzKzucZeER

## Service wallet label precedence

Notcoin checks the **complete Tonkeeper accounts.json** by exact TON address
before applying other blockchain-explorer, contract-interface, or user-supplied
labels. The 2026-11-22 snapshot has 540 source rows, 538 unambiguous accounts
and 235 strictly classified exchange/protocol service entries. Named individuals
remain ordinary holders. Fallback labels retain their source; no exchange
ownership is inferred from balances or highload-wallet contract types.
See [source audit](docs/TONKEEPER_DIRECTORY_AUDIT_2026-11-22.md).

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
Notcoin is registered there with `enabled: true` after the owner confirmed
adding this repository to the existing fine-grained GitHub token. The repository
is public, and the configured cadence is every 30 minutes at :20 / :50 UTC.

This source configuration alone does not prove that Cloudflare has deployed the
latest code or sent an authenticated dispatch. Confirm two successful Notcoin
`workflow_dispatch` launches in GitHub Actions, then remove the temporary
GitHub cron (`17,47 * * * *`) from `.github/workflows/update.yml` to avoid
duplicate updates. Never commit or share the Cloudflare token.

Publishing `index.html` to TON Sites / TON Storage is a separate step,
not performed by GitHub Actions. Until the new repo is public, the standalone
HTML shows its embedded snapshot but cannot fetch new data anonymously from
a private GitHub repository.

## TON Sites HTML size budget

The standalone `index.html` embeds a **bounded offline bootstrap**, not the
complete transaction archive: at most 120 recent swaps, top holder records and
the identity/domain proofs needed to render them. `build.py` rejects pages
larger than **512,000 bytes**. The full verified on-chain data remains in
`data/snapshot.json` and is fetched in the browser from public GitHub after
initial render. If GitHub is temporarily inaccessible, the page can still
open and show its limited cached preview; a partial history is not a complete
30-day seller ranking. Download the newly generated `index.html` for each
TON Sites redeployment; scheduled GitHub updates change only remote data.

## Run locally

```bash
python3 -m scripts.refresh_observatory
python3 build.py
python3 verify.py
python3 -m unittest discover -s tests -p 'test_*.py'
node --check web/app.js
node --test tests/*.test.cjs
```
