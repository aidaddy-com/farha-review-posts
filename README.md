# Farha Review Posts

**Turn every new 5-star review Farha Roofing gets into a ready-to-post Instagram image and caption, in about 5 minutes a week per office.**

It's a Claude skill that's already set up for Farha Roofing:
- **All 8 offices:** Wichita, Kansas City, St. Louis, Denver, Durango, Cañon City, Eads and Phoenix.
- **Farha's own "Client Testimonial" look:** navy and orange, Montserrat, the Farha logo, and the "From Our ___ Market:" tag.
- **Job types:** each post is tagged Commercial, Residential or Multifamily, with a matching photo from Farha's own jobs.
- **Review links:** Google for every office, plus BBB and Yelp where Farha has them.

---

## Setup (5 minutes, one time)

### Step 1: Download this file

**[Download `farha-review-posts.zip`](https://github.com/aidaddy-com/farha-review-posts/raw/main/farha-review-posts.zip)**

This repository is private. You need to be signed in to a GitHub account with access to see the link, or ask AI Daddy to send you the zip.

Leave it as a .zip. Don't unzip it.

### Step 2: Add it to Claude

We recommend the **Claude desktop app with Cowork** ([free download](https://claude.com/download)). Cowork can open your review pages and grab the new reviews for you.

1. In Claude, click **Customize**, then **Skills**.
2. Click **+**, then **Create skill**, then **Upload a skill**.
3. Pick **`farha-review-posts.zip`**.
4. Make sure its switch is **on**.
5. Go to **Settings**, then **Capabilities**, and turn on **"Code execution and file creation"** (it may be called "Create and edit files").

> **On the free Claude plan?** It still works. Paste the new reviews into the chat yourself instead of Claude opening the review pages. Cowork and the browser features need a paid plan (Pro or higher).

<details>
<summary><b>Using ChatGPT instead? Click here.</b></summary>

- **If your ChatGPT has "Skills"** (Business, Enterprise or Edu plans): open **Skills**, click **Create**, then **Upload from your computer**, and pick the zip.
- **If you don't see "Skills":** start a new chat, attach the zip with the paperclip, and type: **"Unzip this and follow the SKILL.md inside to make Farha review posts."** Then paste in your new reviews.

</details>

---

## Every week: just ask

> **Make review posts for Denver**

Or say "all offices". Claude checks that office's Google reviews (plus BBB and Yelp for Wichita and Denver), then gives you:
- **Posts for new 5-star reviews only.** Reviews already turned into posts are skipped.
- **One punchy quote per post,** copied word for word from the review, with the full review on the testimonial card.
- **A caption** for each post, with that office's phone number.
- **An approval sheet** that opens in Excel or Google Sheets, with Approve and Posted columns. It also shows each post's job type and background photo.

**It never posts anything.** You choose what goes out and when.

---

## Commercial, residential or multifamily

Claude reads each review and picks the job type:
- **Multifamily:** words like HOA, condo, apartment or townhome.
- **Commercial:** words like building, office, church, warehouse, TPO or flat roof.
- **Residential:** everything else.

The tag and the background photo follow the job type. If a guess is wrong, just say so:

> **Make post 3 commercial**

> **Make this whole batch commercial**

---

## Good to know

- **New background photos:** send Claude job photos any time and say what they are ("these are commercial"). They go into that type's photo folder and rotate in. Drone and on-site photos work best; avoid screenshots and photos with another company's sign.
- **Customer photos:** if a reviewer attached photos of their roof, that photo becomes the background for their post.
- **Word for word:** reviews are never rewritten. The one exception is BBB, which hides staff names. Those become a plain phrase like "Two reps", and every change is listed in the approval sheet.
- **5-star only:** 4-star and lower reviews are never used.
- **Change the look:** say *"use the testimonial card for all of them"*, *"no two-slide posts"*, or *"fix the crop on post 3"*.

---

## How it was checked (Nov 2026)

- **Matches Farha's own template.** Its testimonial card was overlaid on Farha's real Instagram post: box, text column and margins line up within 2%.
- **Readable on a phone.** No text is cut off in Instagram's 3:4 profile grid, and body text stays at least 24 px (about 9 pt on a phone). Text colors pass WCAG contrast for large text.
- **Job type detection.** Tested on 140 hand-labeled Farha Google reviews from all 8 offices: every review with a clear type came out right, and no home was tagged commercial. Re-run it any time with `python3 tests/job-type/run.py`.
- **Hooks.** `scripts/check_hooks.py` scores every hook before rendering; weak ones get rewritten.
- **Cold test.** A fresh Claude ran the zip on its own ("make review posts for Eads", then "all offices"), and everything it tripped over was fixed.

---

<sub>Fonts: Montserrat, plus fallback Playfair Display, Poppins and Raleway (SIL Open Font License, license files included). Logo, job photos and brand belong to Farha Roofing.</sub>
