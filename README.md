# Personal Coles/Woolworths Price Tracker

Checks up to ~25 grocery items once a day and shows their price history on a
simple mobile-friendly page. Runs entirely on GitHub's free tier — nothing
to host or keep running yourself.

## How it works
- `items.json` — your list of items (name + Coles/Woolworths product URLs)
- `scrape.py` — fetches the current price for each item, appends to `history.json`
- `.github/workflows/daily-check.yml` — runs `scrape.py` once a day automatically
- `index.html` — a page (served by GitHub Pages) that charts `history.json`

## Setup

1. **Create a GitHub account** if you don't have one (github.com — free).

2. **Create a new repository**
   - github.com → New repository → give it a name (e.g. `price-tracker`) → Public → Create.
   - Public is required for free GitHub Pages. Your price data will technically
     be visible to anyone who finds the URL, but it won't be indexed or
     advertised anywhere — it's just not truly private. If that matters to you,
     a paid GitHub plan supports private Pages.

3. **Upload these files** to the repo (drag-and-drop on the repo's main page
   works fine, or use `git push` if you're comfortable with git). Keep the
   folder structure — `.github/workflows/daily-check.yml` needs to stay in
   that exact path.

4. **Fill in `items.json`** with your real items (up to ~25). For each item:
   - **Coles**: search the item on coles.com.au, open the product page, copy
     the URL from your address bar.
   - **Woolworths**: same thing on woolworths.com.au — the URL should look
     like `.../shop/productdetails/123456/product-name`. The number is what
     the script needs.
   - Leave `coles_url` or `woolworths_url` as `""` if you only want to track
     one store for that item.

5. **Turn on GitHub Pages**: repo → Settings → Pages → under "Build and
   deployment", set Source to "Deploy from a branch", branch `main`, folder
   `/ (root)` → Save. GitHub will give you a URL like
   `https://yourusername.github.io/price-tracker/`.

6. **Run it once manually** to test: repo → Actions tab → "Daily price
   check" → Run workflow → Run workflow. Wait a minute, then click into the
   run and check the logs — you'll see `OK` or `FAIL` per item.

7. **If anything shows `FAIL`**: Coles/Woolworths occasionally change their
   page structure, and I couldn't test this live against their current
   site while building it, so the first run is the real test. The error
   message will tell you roughly what broke (e.g. "no pricing block found").
   Common fix: open the product page in Chrome, View Page Source, and search
   for the field name mentioned in the error to see how it's now structured.
   Happy to help you fix it if you paste the error + a snippet of the page source.

8. **On your Android phone**: open your GitHub Pages URL in Chrome, tap the
   ⋮ menu → "Add to Home screen". It'll sit on your home screen with an icon
   like a normal app.

## A couple of honest caveats
- This relies on parts of the Coles/Woolworths sites that aren't officially
  documented for this purpose, so it can break when they change their site —
  it's genuinely a "check back occasionally" tool, not maintenance-free forever.
- Please don't scale this up a lot (many more items, more frequent checks) —
  once a day for ~25 items is very unlikely to cause any issues, but heavier
  use starts looking like the kind of load that gets scrapers blocked.
