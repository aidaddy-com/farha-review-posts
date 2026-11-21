---
name: farha-review-posts
description: Turns Farha Roofing's newest 5-star reviews (Google for each office, plus BBB and Yelp where Farha has them) into ready-to-post Instagram images (1080x1350) in Farha's own "Client Testimonial" brand look, with captions and an approval sheet. Covers all 8 Farha offices (Wichita, Kansas City, St. Louis, Denver, Durango, Cañon City, Eads, Phoenix), asks which office to do, tags each post Commercial, Residential or Multifamily (detected from the review, changeable per post), and uses Farha's own job photos to match. Already set up with Farha's logo, colors, fonts, photos and review links, so there are no setup questions. Use when someone says "make review posts", "new review posts for Denver", "turn our reviews into Instagram posts", "post our 5-star reviews", "make post 3 commercial", or pastes a review and wants a post. It never posts anything itself.
---

# Farha review posts

You're helping someone on the Farha Roofing team, most likely marketing, who is probably **not technical**. Keep messages short and friendly. Never show code, JSON or file paths unless they ask, and do the technical work quietly.

This skill **never posts, publishes or replies** to anything online. The person approves the images and posts them themselves.

Everything is already set up for Farha: logo, brand colors (navy and orange), Montserrat, background photos from Farha's own jobs, and review links for every office. **Don't ask setup questions.**

## 0. Get the Farha folder ready (first time only)

- The tools sit next to this file: `scripts/make_posts.py`, `scripts/check_hooks.py` and `scripts/fonts/`. Below, `{skill}` means the folder this SKILL.md is in.
- **Work in the person's working folder:** `Farha Review Posts/` and `reviews.json` both live there. Run every command from the working folder and call the scripts by their full path, `python3 "{skill}/scripts/…"`.
- The ready-made business folder is `business/`. It holds `settings.json`, the logos, `fonts/`, `photos/`, and `seen.json` (the reviews already turned into posts, so they aren't repeated).
- If there's no `Farha Review Posts/` folder in the working folder yet, **copy `business/` there under that name** and use the copy from now on. In Cowork that's the folder the person picked; it's kept for next time.
- If the person attaches a `seen.json` or `settings.json` from a previous run, put it in that folder first.

Tell the person once, in one line: **"You can change the background photos any time. Just send me job photos and say whether they're commercial, residential or multifamily."**

## 1. Ask which office

Farha has 8 offices, listed in `settings.json` under `locations`:

| Office | Review links |
|---|---|
| Wichita, KS | Google, BBB, Yelp |
| Kansas City, MO | Google |
| St. Louis, MO | Google |
| Denver, CO | Google, BBB |
| Durango, CO | Google |
| Cañon City, CO | Google |
| Eads, CO (Eastern Colorado) | Google |
| Phoenix, AZ | Google |

Ask one question: **"Which office should I do: one of them, a few, or all 8?"** If they already named one ("new posts for Denver"), skip the question.

## 2. Get the newest 5-star reviews

For each chosen office, use its `review_links` in `settings.json`.

**If you have a browser** (Claude in Chrome, or Cowork's browser), open each link and follow `reference/find-reviews.md`. Read only: never click Reply, Like, Report or Write a review. Take about the 10 to 20 newest reviews per office. Small offices (Eads has only a handful) may have nothing new; say so and move on.

**If you can't browse, or a page is blocked:** ask the person to paste the reviews. Say: "Open Farha Roofing <office> on Google Maps, click Reviews, sort by Newest, and paste the last few 5-star reviews here."

Rules:
- **5-star only.** Skip 4-star and lower.
- **Skip reviews with no text,** and never use the owner's reply as the review.
- **Skip reviews that name another company** as the roofer (it happens: "I highly recommend Century Roofing").
- **Skip praise with nothing in it:** reviews of 3 words or fewer with no name or detail ("Good job", "Great company"). Short reviews that name someone or something ("Eric was great, and very knowledgeable!") are fine.
- **The office comes from the listing you read,** except when the review itself names a different Farha office ("Farha Roof Company in the Durango CO location"). Then use the office it names, so the card doesn't contradict the text, and mention it in the hand-over.
- **Same review in two places** (Google and BBB): make **one** post from the Google copy, because BBB hides staff names.
- **Photos with reviews:** if the reviewer attached photos, download the largest version into `photos/from-reviews/` and set `"photo"` on that review. It becomes that post's background. Mention it in the hand-over.
- Reviews already in `seen.json` are skipped automatically. Say how many were new per office.

## 3. Write `reviews.json` (you do this; the person never sees it)

The format is at the top of `scripts/make_posts.py`. For each review:

- **`location`**: the office slug from `settings.json` (`wichita`, `kansas-city`, `st-louis`, `denver`, `durango`, `canon-city`, `eads`, `phoenix`). It sets the "From Our ___ Market:" tag and the source line.
- **`quote`**: the full review, word for word. Never fix spelling or grammar.
- **`hook`**: **the most important field.** It's the one big quote on the image. Rules:
  - 12 words or fewer, copied word for word from the review. You may start partway into a sentence and capitalize its first letter, nothing else.
  - Make it grab attention: specifics beat praise. Look for numbers, names, results, a surprising detail or a strong phrase. Good: "10 guys up and down ladders like a Vegas cirque show", "Turns out I still have some life left in my roof", "We will be using them on our other buildings in the future." Weak: "Great experience from start to finish."
  - Use a different kind of hook from post to post in the same batch so the feed doesn't sound repetitive. Never repeat the same phrase ("in one day") twice in a batch if another strong line exists.
  - If the whole review is 12 words or fewer, the hook can be the whole review.
  - For reviews over 32 words, don't use the opening sentence: the testimonial card prints the full review right under the hook, so it would read twice. Pick a line from later in the review.
  - **Check the batch before rendering:** `python3 "{skill}/scripts/check_hooks.py" reviews.json`. It scores each hook on four points: specific (a number, a time, a person's name or a concrete result), 12 words or fewer, no 3-word phrase shared with another hook, not empty praise. Rewrite every hook marked WEAK or OPENING and run it again. "whole review" lines can't be improved; leave them.
- **`hl`**: a short phrase **inside the hook**, shown in orange. Word for word.
- **`name`**: first name plus last initial ("Sarah M."). Capitalize it ("kathleen Haggerty" becomes "Kathleen H.").
  - Only a first name shown: use it ("Jennifer").
  - Only initials: "J B" becomes "J. B."
  - Drop nicknames in quotes ("mouad “AmbitiousACGuy” boumerzoug" becomes "Mouad B.").
  - A business reviewer keeps its business name ("Lionsgate Management").
  - A couple keeps both first names ("Chuck and Annette L.").
- **`date`**: "Mon YYYY", worked out from "3 weeks ago" using today's date. It goes in the approval sheet only, not on the image.
- **`job`**: leave it out, and the script detects it (see step 4). Set it only when the person tells you, or when the review clearly says what it was and the detector would miss it.
- **Blurred names (BBB only):** BBB shows staff names as "REMOVED". Don't leave "REMOVED" in, and don't guess the name. Prefer a hook that avoids it; otherwise swap in the plainest role word that reads naturally, with no brackets ("REMOVED and REMOVED with Farha" becomes "Two reps with Farha"). Write it as `"edits": [{"from": "...", "to": "..."}]`. It's listed in the approval sheet.
- **`caption`**: under 80 words, warm, professional and plain.
  - Thank the reviewer by first name (or business name).
  - Mention one specific thing from the review. Never invent details (job type, city, names, roof system) that aren't in the review.
  - End with `Free roof inspection: call our <office> office at <phone>` using that office's `phone` from `settings.json`.
  - Then 3 to 5 hashtags: `#FarhaRoofing`, one of the office's `hashtags`, and one or two from the post's job type (`job_types.<type>.hashtags`). Don't use `#CommercialRoofing` on a home job.

## 4. Job type: commercial, residential or multifamily

Every post gets a navy tag ("Commercial Project", "Residential Project" or "Multifamily Project"), and the background photo comes from that type's photo folder.

**How it's detected** (from the review's own words, and a business reviewer's name, when `job` isn't set):
- **Multifamily:** apartment, condo, townhome, multi family, 4-plex, several HOAs, or an HOA as the client ("roof replacement for our Homeowner Association"). Also residents, units or "communities I manage" when no house is mentioned.
  - A single house that happens to be in an HOA, or a townhouse apartment attached to someone's house, is residential.
- **Commercial:** our office, office building, warehouse, church, school, store, sports bar, medical, facility, tenants, "our staff", "our company", "roofing vendor", "commercial", flat roofing.
  - Roof materials (TPO, EPDM, PVC, membrane) count only when the review never mentions a house, because homes get TPO porches and sunrooms too.
  - Farha's own office doesn't count: "the office", "office staff", "the Canon City office".
  - Praise for both ("great for residential or commercial projects") isn't a clue.
- **No clues in the text:** a business name decides it ("Ethans Apartments" is multifamily, "Delano Storage" is commercial). Otherwise residential, since most reviews are homes.

Measured in Nov 2026 on 140 hand-labeled Farha reviews from all 8 offices: all 99 with a clear type came out right, and no home was tagged commercial. The rules were tuned on those same reviews (a fresh batch scored 82% before the last fixes), so expect a few misses on new wording; the approver catches them in the sheet.

The approval sheet shows the job type, the words that decided it ("auto: condominium") and the background photo used, so the approver can catch a wrong guess.

**The person can change it any time.** Map what they say to the fix and run again:
- "Make post 3 commercial" → set `"job": "commercial"` on that review.
- "Make this whole batch commercial" → add `--job commercial`.
- "That one is an apartment complex" → `"job": "multifamily"`.

Tell them about the job type in one line during the hand-over, and flag any review where you're unsure (for example "a handful of jobs we've worked with them on" reads like a business client, but doesn't say so).

## 5. Make the images

```bash
pip install pillow   # only if "Pillow is missing" appears
python3 "{skill}/scripts/make_posts.py" --folder "Farha Review Posts" reviews.json
```

Add `--location <slug>` to make one office only from a mixed file. The script prints the output folder: `Farha Review Posts/posts/<date>/`, or `<date>-<office>` with `--location`. A second run on the same day gets its own folder (`<date>-2`), so an earlier batch is never overwritten.

Layout is automatic:
- **Reviews up to 32 words:** photo on top, the hook big underneath ("photo and quote").
- **Longer reviews:** Farha's "Client Testimonial" card, with the hook in the navy box and the full review under "Here's how we helped."
- **Reviews of 60+ words:** a 2-slide carousel. Slide 1 is the photo with the hook; slide 2 is the testimonial card with the full review (it doesn't repeat the hook).

If they ask for a different look, add `--template split|market|auto` or `--carousel off|long-only|always`.

Very long reviews: if the full review won't fit on the card at a size people can read on a phone, the card shows the first whole sentences that fit and ends with "…". The approval sheet's "card note" column says so; the full review stays in `captions.md`.

**Look at every image before showing it.** Check for cut-off text, an awkward photo crop (a yard sign or logo cut in half at the edge), a photo that shows another company's sign, or stray "REMOVED". To fix a crop, set `photo_focus` for that photo in `settings.json`, then run again.

## 6. Hand over

1. Show the images grouped per post, with each caption underneath.
2. Give them this run's output folder (the one the script printed) to download, zipped if you can make a zip. It includes `approval.csv` (opens in Excel or Google Sheets) and `captions.md`.
3. Tell them in plain words, in 5 lines or fewer:
   - How many posts per office, and how many are carousels
   - The job type of each post, and any you're unsure about
   - Anything skipped or edited
   - That nothing was posted, so they review and post themselves
   - The next step: "Next week just say 'make review posts for <office>' and I'll grab the new ones."
