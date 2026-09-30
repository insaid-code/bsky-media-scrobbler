# 📊 Statistics, Balance Reports, and Visual Collages

`bsky-media-scrobbler` includes a comprehensive analytics engine that tracks your media habits, calculates closed natural reporting periods, composes high-definition poster collages, and celebrates viewing milestones on your Bluesky timeline.

---

## 🗓️ Periodic Publication Schedule

| Report | Scheduled Time | Analyzed Window | Format & Highlights |
| :--- | :--- | :--- | :--- |
| **Weekly Balance** | **Mondays at 09:30h** *(or after)* | Full closed natural week (Monday 00:00 to Sunday 23:59:59) | Poster grid collage (**3x3** or **2x2**), watched episodes, total minutes & hours, finished movies, and completed seasons. |
| **Monthly Balance** | **1st of month at 09:30h** *(or after)* | Full closed natural month (1st 00:00 to month end 23:59:59) | Visual collage, total monthly minutes, completed series, and movies watched during the previous month. |
| **Mid-Month Fun Fact** | **15th of month at 12:00h** *(or after)* | Consolidated historical data | Rotating analytics: peak binge weekday, peak marathon hour, longest show completed (loyalty medal), or catalog completion rate. |
| **Viewing Streaks** | Upon daily activity sync | Consecutive active days | Celebrates streaks when reaching **7 continuous days** and weekly milestones thereafter (14, 21, 28...). |
| **All-Time Milestones** | Real-time after finishing items | Global historical tally | Celebrates major milestones (e.g., 18,000 episodes, 400 completed shows, 450 movies). |

---

## 🖼️ Automated Poster Collages (Pillow)

The engine generates composite image files optimized for Bluesky (`collage.py`):

1. **3x3 Grid (Default):**
   * Displays up to **9 posters** in standard 2:3 portrait aspect ratio.
   * Final dimensions: **1200 x 1800 px** in high-quality JPEG with adaptive compression `< 950 KB` (safely below Bluesky upload limits).
   * Smart layout: Prioritizes distinct TV shows and movies watched during the period. Automatically downgrades to 2x2 if fewer than 9 distinct posters are available.
2. **2x2 Grid:**
   * Displays **4 main posters**.
   * Final dimensions: **1200 x 1800 px**.
   * Perfect for weeks focused on 2–4 titles or deep single-show binges.

---

## ⚡ Manual Signal Triggers

You do not need to wait for Monday or the 1st of the month to preview balance reports. The scrobbler checks `/data` every 5 seconds for ephemeral trigger files:

### 1. Force Weekly Summary
```bash
# Standard 3x3 grid
echo "3x3" > /Volumes/docker/bsky-media-scrobbler/data/trigger_weekly

# Or compact 2x2 grid
echo "2x2" > /Volumes/docker/bsky-media-scrobbler/data/trigger_weekly
```

### 2. Force Monthly Summary
```bash
# Standard 3x3 grid
echo "3x3" > /Volumes/docker/bsky-media-scrobbler/data/trigger_monthly

# Or compact 2x2 grid
echo "2x2" > /Volumes/docker/bsky-media-scrobbler/data/trigger_monthly
```

### 3. Force Fun Fact / Curiosity
```bash
touch /Volumes/docker/bsky-media-scrobbler/data/trigger_fun_fact
```

> **Automatic cleanup:** The container detects the signal file within seconds, generates and uploads the report to Bluesky, and deletes the trigger file to prevent duplicate runs.
