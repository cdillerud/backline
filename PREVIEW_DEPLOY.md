# Backline visual preview (isolated from production)

This release contains an interactive stage designer, show packets, PDF document vault, tour
routing, booking CRM and AI Gig Studio foundations.

## Deployment boundary

**Never use `fly.toml` or `-a backline` for this preview.** The existing production
app uses a persistent `backline_data` volume. The visual preview uses the separately
named `backline-visual-preview` app, `fly.preview.toml`, and **no volume mount**.
It generates fictional sample data and is deliberately disposable.

The preview relies on a randomly generated private HTTP Basic Auth password. Do not
put real contracts, W-9s, personal information or important band data into this demo.
The demo database can disappear on a Fly Machine restart/replacement.

## Deploy using PowerShell 7

Prerequisites: `git`, `flyctl` and an authenticated Fly.io account with authority to
create a new app (new Fly apps may incur hosting charges).

```powershell
git clone https://github.com/cdillerud/backline.git
cd backline
git switch integration/backline-v0-4-rc
flyctl auth login
./scripts/deploy-preview.ps1
```

If you already have the repository checked out, switch to the branch and run the script.
It generates and prints the preview password once locally.

Open `https://backline-visual-preview.fly.dev`, authenticate with `preview` and the
generated password, then select **Show Packets** to try the visual stage editor and
**Tour Routing** to explore the fictional Upper Midwest itinerary.

## Validation and rollback

```powershell
flyctl status -a backline-visual-preview
flyctl logs -a backline-visual-preview
flyctl apps destroy backline-visual-preview
```

Destroy only the *preview* app when no longer needed. Do not pass `-a backline`.
Automated API and Chromium tests run in GitHub Actions on the integration branch.
Passing CI is necessary but not a replacement for real-browser acceptance and
security review. No account-mode migration is involved in this preview.
