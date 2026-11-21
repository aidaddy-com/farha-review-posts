# Finding the newest Farha reviews in a browser

This works with any browser tool: Claude in Chrome, Cowork's browser, or ChatGPT's agent browser.

General rules:
- Work in a new tab and close it when done.
- Read only. Never click Reply, Like, Share, Report, or "Write a review".
- Prefer `get_page_text`, `find` and `read_page` over screenshots. Use `javascript_tool` only to read the page, never to change it. Clicking "More", the Reviews tab and the Sort menu is fine; those only change what's shown.
- Collect the newest 10 to 20 reviews per office, then stop.
- Each office has its own Google listing. The office comes from the link you opened, unless the review itself names a different Farha office (see SKILL.md step 2).

## Google Maps (every office)

1. Open the office's Google link from `settings.json`. If a consent banner shows, choose **Reject all**.
2. Click the **Reviews** tab (`find` "Reviews").
3. Sort by newest: click the **Sort** button, then the **Newest** menu item.
4. **Scroll the review list**, not the map. The list is the tallest scrolling panel on the left. Cards load as you scroll. Setting `scrollTop` from JavaScript sometimes loads nothing; if the card count doesn't grow, use real mouse-wheel scrolls (`computer` → `scroll`) with the pointer over the list.
5. Expand long reviews: click every **More** / **See more** button in the list (`button.w8nwRe` in Nov 2026).
6. Read the cards. This `javascript_tool` snippet worked in Nov 2026 (Google changes its page often; if it returns nothing, fall back to `get_page_text`):

```js
[...document.querySelectorAll('div.jftiEf')].map(r => ({
  name: r.getAttribute('aria-label'),
  stars: r.querySelector('.kvMYJc')?.getAttribute('aria-label'),   // "5 stars"
  when: r.querySelector('.rsqaWe')?.textContent,                    // "3 weeks ago"
  text: r.querySelector('.MyEned .wiI7pd')?.textContent || ''       // empty = no text
})).filter(x => x.text && x.stars === '5 stars')
```

   Tool output can be cut off around 1,000 characters. Two ways around it:
   - Save the list in `window.__r` first, then read a few reviews at a time.
   - Or write the list into the page as plain text and read it in one go with `get_page_text`:
     `document.body.innerHTML = '<article><pre>' + list.map(x => x.name + ' | ' + x.stars + ' | ' + x.when + '\n' + x.text).join('\n') + '</pre></article>'`.
     This only changes your own copy of the page; reload it to get the map back.
7. Ignore "Response from the owner". It is not part of the review. A review with no text of its own is skipped.

Notes:
- "Translated by Google": use the original text, or skip the review.
- Emojis in reviews are fine: the image leaves them out (the fonts can't draw them) and the captions file keeps them.

## BBB (Wichita and Denver)

1. Open the BBB link. A "Just a moment…" check shows first. Wait about 5 to 10 seconds and it passes on its own. If it asks you to tick a box or solve a puzzle, stop and ask the person to open the page.
2. Pick **Most recent** in the sort control if it isn't already selected.
3. Read the page with `get_page_text`. Each review reads: "Review from", the name, "Date: MM/DD/YYYY", "5 stars", then the text. Filter on "5 stars".
4. Some reviews start with emoji stars that show up as "?????". Drop that leading run.
5. **Redactions:** BBB blurs staff names. In the text they read "REMOVED". Keep "REMOVED" in `quote`; step 3 of SKILL.md explains how to swap it with `edits`.
6. Most BBB reviews are also on Google. Check for duplicates and keep the Google copy.
7. Complaints live on a separate tab. Ignore them.

## Yelp (Wichita)

1. Open the Yelp link. Yelp sometimes blocks automated browsers; if it shows a check you can't pass, skip Yelp and say so.
2. Sort by **Newest first**, then read name, date, star rating (from the star image's `aria-label`) and the full text.
3. Yelp has only a few Farha reviews, so it rarely has anything new.
