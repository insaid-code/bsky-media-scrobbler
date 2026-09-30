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
echo "3x3" > data/trigger_weekly

# Or compact 2x2 grid
echo "2x2" > data/trigger_weekly
```

### 2. Force Monthly Summary
```bash
# Standard 3x3 grid
echo "3x3" > data/trigger_monthly

# Or compact 2x2 grid
echo "2x2" > data/trigger_monthly
```

### 3. Force Fun Fact / Curiosity
```bash
touch data/trigger_fun_fact
```

> **Automatic cleanup:** The container detects the signal file within seconds, generates and uploads the report to Bluesky, and deletes the trigger file to prevent duplicate runs. You can also trigger them via Docker: `docker exec bsky-media-scrobbler touch /data/trigger_fun_fact`.

---

## 🎛️ Dashboard Integration (OliveTin / HomeLab)

If you use a web action dashboard such as **OliveTin**, you can add dedicated action buttons to your `config.yaml` to trigger these balance runs with a single click:

```yaml
  # --- BLUESKY MEDIA SCROBBLER ---
  - title: "🦋 Bluesky: Force Monthly Balance"
    icon: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='24' height='24'><path fill='#1185fe' d='M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566 1.018 1.561 1.748 1.561 3.254c0 3.28 1.83 13.435 8.439 13.435 3.398 0 4.887-2.98 5.86-5.889z'/></svg>"
    shell: "echo '{{ grid }}' > /path/to/bsky-media-scrobbler/data/trigger_monthly && echo 'Monthly trigger sent with {{ grid }} collage'"
    timeout: 30
    arguments:
      - name: grid
        title: "Grid Type"
        choices:
          - title: "🎨 3x3 Grid (9 posters)"
            value: "3x3"
          - title: "🖼️ 2x2 Grid (4 posters)"
            value: "2x2"

  - title: "🦋 Bluesky: Force Fun Fact / Curiosity"
    icon: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='24' height='24'><path fill='#f59e0b' d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z'/></svg>"
    shell: "touch /path/to/bsky-media-scrobbler/data/trigger_fun_fact && echo 'Fun fact trigger sent to scrobbler.'"
    timeout: 15
```
