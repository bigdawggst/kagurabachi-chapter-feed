# Kagurabachi chapter feed: setup

This is a small **prototype** which checks [VIZ's official Kagurabachi chapter list](https://www.viz.com/shonenjump/chapters/kagurabachi), then publishes an RSS entry for newly listed released chapters. The RSS entry links to the official [MANGA Plus](https://mangaplus.shueisha.co.jp/titles/700020) series page.

## Run it once before connecting MonitoRSS
1. In GitHub open **Actions**.
2. Choose **Update Kagurabachi chapter RSS** > **Run workflow** on the `main` branch.
3. Wait for the run to finish. The first successful run writes `state.json` and **does not ping for old chapters**.
4. Confirm `chapters.xml` loads at:
   https://raw.githubusercontent.com/bigdawggst/kagurabachi-chapter-feed/main/chapters.xml
5. If the workflow fails, open the failed job and review the log. Do not enable role pings until the live VIZ fetch succeeds.

## Subscribe with MonitoRSS
1. Add the URL above as an RSS feed.
2. Destination Discord channel: `#kagurabachi-news`.
3. Use a spoiler-free Rich Embed or simple text message; the RSS title contains the new chapter number.
4. The **Manga Ping role mention** belongs in normal message content, outside the embed; the bot must be allowed to mention it.
5. Test with a non-production role or a test channel before enabling live pings.

## Separate all-news feed (no ping)
Subscribe MonitoRSS to:
https://news.google.com/rss/search?q=Kagurabachi&hl=en-US&gl=US&ceid=US%3Aen

Destination: `#kagurabachi-news`. No role mention.

## Cautions
- This is **not** a live-tested official chapter API. Changes to VIZ's HTML or access restrictions can break the parser.
- A scheduled publication date alone does not prove a release is available; VIZ listing and the configured release time are a proxy. Check a live run before enabling automatic pings.
- GitHub Actions and MonitoRSS checking may be delayed.
- The first successful run intentionally publishes an **empty** feed. If MonitoRSS rejects an empty RSS feed, stop and report the error rather than adding a fake chapter entry.
- GitHub may need Actions enabled; workflow needs `contents: write` to commit state. You can disable the workflow from the Actions tab to stop future checks.
