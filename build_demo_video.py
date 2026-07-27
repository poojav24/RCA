"""
NZCC Client Demo — rebuild
- Smooth human-like scrolling synced to narration
- Real mouse hover + soft highlight (no drawn pointer cursor)
- Narration only describes what is on each page (top → bottom)
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts
import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "demo_video_assets"
FRAMES_DIR = OUT_DIR / "frames"
AUDIO_DIR = OUT_DIR / "audio"
CLIPS_DIR = OUT_DIR / "clips"
FINAL_MP4 = ROOT / "NZCC_Client_Demo.mp4"
BASE_URL = os.environ.get("NZCC_DEMO_URL", "http://127.0.0.1:8001/")
VOICE = "en-US-JennyNeural"
WIDTH, HEIGHT = 1280, 720
FPS = 15

# Beats are top→bottom. selector = CSS to scroll + hover. view=None = title card.
SCENES = [
    {
        "id": "00_intro",
        "view": None,
        "title": "Near Zero Command Center",
        "beats": [
            {
                "text": (
                    "Hey everyone — welcome to the Near Zero Command Center, our enterprise A I Ops platform. "
                    "I'll walk each page from top to bottom, and as I talk you'll see the page scroll and hover on that section. "
                    "Near Zero watches Zabbix alerts, links ServiceNow, pulls metrics and Loki logs, runs A I root cause, "
                    "and after resolve stores learning in Knowledge with a vector D B update."
                ),
                "selector": None,
            }
        ],
    },
    {
        "id": "01_dashboard",
        "view": "dashboard",
        "title": "Dashboard",
        "beats": [
            {
                "text": "We're on the Dashboard — Executive Overview. Up in the top bar, this bell is the notification icon — new alerts and investigation updates show up here with a little badge.",
                "selector": "#notify-bell",
            },
            {
                "text": "The page title is Executive Overview — real-time visibility into alerts, investigations, and A I root cause analysis, with a Refresh button on the right.",
                "selector": "#view-dashboard .page-header",
            },
            {
                "text": "These K P I cards are first: today's alerts, open, resolved, critical, average R C A time, connected hosts, knowledge entries, reuse rate, technologies, and backend status.",
                "selector": "#kpi-grid",
            },
            {
                "text": "Next row — Alert Trend chart for operational load, and Severity Distribution for the current workload mix.",
                "selector": "#trend-chart",
            },
            {
                "text": "Then Technology Distribution for active platforms, and Incident Status — the operational pulse with health and workload signals.",
                "selector": "#technology-chart",
            },
            {
                "text": "Below that, Top Affected Hosts from the knowledge repository, and Latest Investigations — you can select one to open R C A.",
                "selector": "#top-hosts",
            },
            {
                "text": "Recent Activity Timeline lists investigation events as they land.",
                "selector": "#activity-timeline",
            },
            {
                "text": "And at the bottom, Platform Connectivity shows backend integration status — alert ingestion, I T S M, logs, knowledge, and the A I engine.",
                "selector": "#backend-health",
            },
        ],
    },
    {
        "id": "02_investigation",
        "view": "investigation",
        "title": "Live Investigation",
        "need_alert": True,
        "beats": [
            {
                "text": "Live Investigation is the active workspace. Header says end-to-end A I investigation with live evidence — you can jump to Select Alert or hit Refresh.",
                "selector": "#view-investigation .page-header",
            },
            {
                "text": "Current Investigation holds the alert context — host, severity, technology, identifiers, and ServiceNow linkage.",
                "selector": "#investigation-summary",
            },
            {
                "text": "A I Investigation Pipeline shows animated stage progress across the full flow, with the progress label and horizontal chips.",
                "selector": "#investigation-pipeline-h",
            },
            {
                "text": "Stage Detail breaks each step down, and Investigation Timeline shows when stages completed.",
                "selector": "#investigation-pipeline",
            },
            {
                "text": "Evidence Summary, Collected Metrics, and Historical Matches sit side by side — proof plus prior cases.",
                "selector": "#evidence-cards",
            },
            {
                "text": "Log Intelligence lists recent Loki lines for this host.",
                "selector": "#recent-logs",
            },
            {
                "text": "At the bottom, A I Root Cause Analysis shows the live root cause block for this investigation.",
                "selector": "#investigation-rca",
            },
        ],
    },
    {
        "id": "03_alerts",
        "view": "alerts",
        "title": "Active Alerts",
        "beats": [
            {
                "text": "Active Alerts is the live inventory — severity, technology, and I T S M linkage in one place.",
                "selector": "#view-alerts .page-header",
            },
            {
                "text": "Alert Workbench filters let you search host or problem, and filter by severity, status, and technology.",
                "selector": "#alerts-search",
            },
            {
                "text": "The table lists severity, host, problem, technology, trigger, event, ServiceNow, status, and time. Click a row to open the full R C A.",
                "selector": "#alerts-table",
            },
        ],
    },
    {
        "id": "04_rca",
        "view": "rca",
        "title": "RCA Analysis",
        "need_alert": True,
        "beats": [
            {
                "text": "R C A Analysis is the primary investigation brief. Up top you've got Live View, Refresh, and Export P D F — that downloads a P D F of this R C A report for sharing or audit.",
                "selector": "#export-rca",
            },
            {
                "text": "Also keep an eye on the notification bell in the top bar — when investigation status changes, it lights up here.",
                "selector": "#notify-bell",
            },
            {
                "text": "Starting from the top of the brief — Alert Summary with problem, host, technology, severity, trigger, event, ServiceNow, and investigation duration.",
                "selector": "#rca-body .card",
                "nth": 0,
            },
            {
                "text": "Scrolling smoothly to Investigation Pipeline — the stage chips for this incident.",
                "selector": "#rca-body .pipeline-horizontal",
            },
            {
                "text": "Next, Metrics Summary — collected metric cards with values — and beside it Log Summary from Loki.",
                "selector": "#rca-body .metrics-grid",
            },
            {
                "text": "Further down, Historical Similar Incidents — top matches with similarity percent, technology, and prior root cause.",
                "selector": "#rca-body .incidents-grid",
            },
            {
                "text": "Evidence Sources shows what's available: alert context, I T S M, metrics, logs, historical intelligence, and the A I engine.",
                "selector": "#rca-body .evidence-grid",
            },
            {
                "text": "A I Root Cause is the main block — root cause text, business impact, and confidence meter.",
                "selector": "#rca-body .rca-main",
            },
            {
                "text": "Recommended Resolution lists the fix steps, and Validation Checklist is what to verify after the change.",
                "selector": "#rca-body .resolution-steps",
            },
            {
                "text": "Investigation Statistics wraps counts for metrics, log entries, similar cases, and confidence. And again — Export P D F downloads this whole report as a P D F file.",
                "selector": "#export-rca",
            },
        ],
    },
    {
        "id": "05_knowledge",
        "view": "knowledge",
        "title": "Knowledge Repository",
        "beats": [
            {
                "text": "Knowledge Repository stores resolved investigations that power historical incident intelligence.",
                "selector": "#view-knowledge .page-header",
            },
            {
                "text": "Indexed Investigations — search problem or root cause, filter technology, severity, date, and confidence. After resolve, Near Zero updates the vector D B so these stay searchable.",
                "selector": "#knowledge-search",
            },
            {
                "text": "The table shows problem, technology, severity, root cause, occurrences, similarity, confidence, and last seen.",
                "selector": "#knowledge-table",
            },
        ],
    },
    {
        "id": "06_search",
        "view": "search",
        "title": "AI Search",
        "beats": [
            {
                "text": "A I Search is conversational lookup across past incidents and resolutions.",
                "selector": "#view-search .page-header",
            },
            {
                "text": "Type a question in this box — ask about a host, a root cause, or a technology — and you'll get an A I answer with retrieved evidence underneath.",
                "selector": "#search-input",
            },
        ],
    },
    {
        "id": "07_metrics",
        "view": "metrics",
        "title": "Metrics Explorer",
        "beats": [
            {
                "text": "Metrics Explorer — filter by host, technology, time range, or metric name.",
                "selector": "#metrics-host",
            },
            {
                "text": "K P I cards and category tiles sit up top for a quick read of C P U, memory, disk, and related signals.",
                "selector": "#metrics-kpi",
            },
            {
                "text": "Trend chart and status grid, then the full metrics table below for the detail.",
                "selector": "#metrics-table",
            },
        ],
    },
    {
        "id": "08_logs",
        "view": "logs",
        "title": "Logs Explorer",
        "beats": [
            {
                "text": "Logs Explorer is the Loki viewer. Filters cover host, technology, severity, time range, and keyword search.",
                "selector": "#logs-host",
            },
            {
                "text": "Stats cards, then the log list with error and warning highlighting as you scroll the stream.",
                "selector": "#logs-list",
            },
        ],
    },
    {
        "id": "09_servicenow",
        "view": "servicenow",
        "title": "ServiceNow",
        "beats": [
            {
                "text": "ServiceNow page is the I T S M bridge — search incidents and filter by priority.",
                "selector": "#servicenow-search",
            },
            {
                "text": "The table shows ticket number, priority, state, assignment, and short description linked to monitoring.",
                "selector": "#servicenow-table",
            },
        ],
    },
    {
        "id": "10_analytics",
        "view": "analytics",
        "title": "Analytics",
        "beats": [
            {
                "text": "Analytics opens with K P I cards for volumes and trends.",
                "selector": "#analytics-kpi",
            },
            {
                "text": "Alert Distribution Trend and Technology Distribution charts sit next.",
                "selector": "#analytics-trend",
            },
            {
                "text": "Then Most Common Root Causes and Most Frequent Technologies — useful for spotting repeat patterns.",
                "selector": "#analytics-causes",
            },
        ],
    },
    {
        "id": "11_roadmap",
        "view": "roadmap",
        "title": "Roadmap",
        "beats": [
            {
                "text": "Roadmap lays out completed work, what's in flight, and what's planned for the platform.",
                "selector": "#view-roadmap .page-header",
            },
            {
                "text": "Scroll the roadmap cards to see delivery status for upcoming capabilities.",
                "selector": "#view-roadmap",
                "scroll_ratio": 0.45,
            },
        ],
    },
    {
        "id": "12_settings",
        "view": "settings",
        "title": "Settings",
        "beats": [
            {
                "text": "Settings — Backend Integration has the backend U R L and polling interval in seconds.",
                "selector": "#backend-url",
            },
            {
                "text": "Experience covers theme, toast notifications, and demo mode.",
                "selector": "#theme-select",
            },
            {
                "text": "System Information shows product name, version, backend status, last updated, polling, knowledge count, and active alerts.",
                "selector": "#view-settings .system-info",
            },
        ],
    },
    {
        "id": "13_close",
        "view": None,
        "title": "Thanks for watching",
        "beats": [
            {
                "text": (
                    "Alright — that's the full tour, top to bottom on every page. "
                    "From the dashboard and notification bell, through live investigation and alerts, "
                    "into the R C A brief you can download as a P D F, then knowledge with vector D B learning, "
                    "search, metrics, logs, ServiceNow, analytics, roadmap, and settings. "
                    "Thanks for watching — happy to do a live walkthrough whenever you're ready."
                ),
                "selector": None,
            }
        ],
    },
]


def ensure_dirs() -> None:
    for d in (OUT_DIR, FRAMES_DIR, AUDIO_DIR, CLIPS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


async def synthesize(text: str, out_mp3: Path, out_wav: Path) -> float:
    communicate = edge_tts.Communicate(text, VOICE, rate="-5%")
    await communicate.save(str(out_mp3))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-i", str(out_mp3), "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1", str(out_wav)],
        check=True,
        capture_output=True,
    )
    return wav_duration(out_wav)


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("segoeui.ttf", "arial.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_title_card(title: str, subtitle: str) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), (8, 14, 28))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        c = int(8 + (y / HEIGHT) * 28)
        draw.line([(0, y), (WIDTH, y)], fill=(c, 18 + c // 3, 40 + c // 2))
    title_font = load_font(46)
    sub_font = load_font(24)
    brand_font = load_font(18)
    draw.text((72, 230), "NEAR ZERO COMMAND CENTER", fill=(120, 190, 255), font=brand_font)
    draw.text((72, 275), title, fill=(245, 248, 255), font=title_font)
    draw.text((72, 355), subtitle, fill=(180, 195, 220), font=sub_font)
    draw.rectangle([72, 420, 220, 426], fill=(56, 160, 255))
    return img


def draw_caption(img: Image.Image, caption: str) -> Image.Image:
    out = img.copy()
    draw = ImageDraw.Draw(out, "RGBA")
    font = load_font(20)
    text = caption[:80]
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x0, y0 = 36, HEIGHT - th - 40
    pad = 12
    draw.rounded_rectangle(
        [x0 - pad, y0 - pad, x0 + tw + pad, y0 + th + pad],
        radius=8,
        fill=(6, 12, 24, 190),
    )
    draw.text((x0, y0), text, fill=(235, 242, 255, 255), font=font)
    return out.convert("RGB")


def ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


def mux_av(video: Path, audio: Path, out: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-i", str(video), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)],
        check=True,
        capture_output=True,
    )


def concat_videos(paths: list[Path], out: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    lst = OUT_DIR / "concat.txt"
    lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in paths), encoding="utf-8")
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)],
        check=True,
        capture_output=True,
    )


async def goto_view(page, view: str) -> None:
    btn = page.locator(f'button.nav-item[data-view="{view}"]')
    if await btn.count():
        await btn.first.click()
    else:
        await page.evaluate(
            """(v) => {
              const b = document.querySelector(`button[data-view="${v}"]`);
              if (b) b.click();
              if (window.setActiveView) window.setActiveView(v);
              if (window.renderCurrentView) window.renderCurrentView();
            }""",
            view,
        )
    await page.wait_for_timeout(700)


async def ensure_alert(page) -> None:
    await goto_view(page, "alerts")
    await page.wait_for_timeout(600)
    row = page.locator("#alerts-table tbody tr").first
    if await row.count():
        await row.click()
        await page.wait_for_timeout(900)


async def clear_hover(page) -> None:
    await page.evaluate(
        """() => {
          document.querySelectorAll('.nzcc-demo-hover').forEach(el => el.classList.remove('nzcc-demo-hover'));
        }"""
    )


async def get_scroll_state(page) -> float:
    return await page.evaluate(
        """() => {
          const main = document.querySelector('.content-area');
          return main ? main.scrollTop : (document.scrollingElement?.scrollTop || 0);
        }"""
    )


async def set_scroll(page, y: float) -> None:
    await page.evaluate(
        """(y) => {
          const main = document.querySelector('.content-area');
          if (main) main.scrollTop = y;
          else if (document.scrollingElement) document.scrollingElement.scrollTop = y;
        }""",
        max(0, y),
    )


async def resolve_target(page, selector: str | None, nth: int = 0, scroll_ratio: float | None = None) -> dict:
    """Return target scrollTop and hover viewport x,y."""
    if scroll_ratio is not None and not selector:
        return await page.evaluate(
            """(r) => {
              const main = document.querySelector('.content-area');
              const max = main ? (main.scrollHeight - main.clientHeight) : 0;
              return { scrollTop: max * r, x: 640, y: 360, ok: true };
            }""",
            scroll_ratio,
        )

    if not selector:
        return {"scrollTop": 0, "x": WIDTH / 2, "y": HEIGHT / 2, "ok": False}

    return await page.evaluate(
        """({ selector, nth, scrollRatio }) => {
          const main = document.querySelector('.content-area');
          const nodes = Array.from(document.querySelectorAll(selector)).filter(el => {
            const s = getComputedStyle(el);
            return s.display !== 'none' && s.visibility !== 'hidden';
          });
          const el = nodes[Math.min(nth, Math.max(nodes.length - 1, 0))];
          if (!el) {
            const max = main ? (main.scrollHeight - main.clientHeight) : 0;
            return { scrollTop: scrollRatio != null ? max * scrollRatio : (main?.scrollTop || 0), x: 640, y: 360, ok: false };
          }
          const mainRect = main ? main.getBoundingClientRect() : { top: 0, left: 0, height: window.innerHeight };
          const rect = el.getBoundingClientRect();
          const current = main ? main.scrollTop : (document.scrollingElement?.scrollTop || 0);
          // place element ~18% from top of content area
          let target = current + (rect.top - mainRect.top) - Math.max(56, mainRect.height * 0.12);
          if (scrollRatio != null && main) {
            const max = main.scrollHeight - main.clientHeight;
            target = max * scrollRatio;
          }
          const maxScroll = main ? Math.max(0, main.scrollHeight - main.clientHeight) : 0;
          target = Math.max(0, Math.min(target, maxScroll));
          // After scroll, approximate hover point near top-center of element
          const hoverY = Math.min(Math.max(rect.top + Math.min(36, rect.height * 0.3), 100), window.innerHeight - 80);
          const hoverX = Math.min(Math.max(rect.left + rect.width * 0.4, 80), window.innerWidth - 80);
          return { scrollTop: target, x: hoverX, y: hoverY, ok: true, selector };
        }""",
        {"selector": selector, "nth": nth, "scrollRatio": scroll_ratio},
    )


async def apply_hover(page, selector: str | None, nth: int = 0, x: float = 0, y: float = 0) -> None:
    await clear_hover(page)
    if selector:
        await page.evaluate(
            """({ selector, nth }) => {
              const nodes = Array.from(document.querySelectorAll(selector)).filter(el => {
                const s = getComputedStyle(el);
                return s.display !== 'none' && s.visibility !== 'hidden';
              });
              const el = nodes[Math.min(nth, Math.max(nodes.length - 1, 0))];
              if (!el) return;
              let target = el;
              // Prefer card / interactive parent for nicer hover frame
              const card = el.closest('.card, .kpi-card, button, .metric-card, table, .chat-card');
              if (card) target = card;
              target.classList.add('nzcc-demo-hover');
            }""",
            {"selector": selector, "nth": nth},
        )
    try:
        await page.mouse.move(float(x), float(y), steps=8)
    except Exception:
        pass


async def record_title_clip(title: str, duration: float, out_path: Path) -> None:
    card = draw_title_card(title, "Enterprise AIOps · Client Walkthrough")
    card = draw_caption(card, title)
    writer = imageio.get_writer(
        str(out_path), fps=FPS, codec="libx264", quality=8, pixelformat="yuv420p", macro_block_size=1
    )
    n = max(int(duration * FPS), 1)
    arr = np.array(card)
    for _ in range(n):
        writer.append_data(arr)
    writer.close()


async def record_ui_beat(page, beat: dict, duration: float, title: str, out_path: Path) -> None:
    """Smooth scroll + hover for the length of the narration."""
    selector = beat.get("selector")
    nth = int(beat.get("nth") or 0)
    scroll_ratio = beat.get("scroll_ratio")

    start_scroll = await get_scroll_state(page)
    # Peek target without scrolling first
    target = await resolve_target(page, selector, nth, scroll_ratio)
    end_scroll = float(target["scrollTop"])

    # Mouse start near previous position / center-left
    mx0, my0 = WIDTH * 0.25, HEIGHT * 0.35
    mx1, my1 = float(target["x"]), float(target["y"])

    n = max(int(duration * FPS), 8)
    # Phase A: scroll 0→0.55, Phase B: settle hover 0.55→1
    writer = imageio.get_writer(
        str(out_path), fps=FPS, codec="libx264", quality=8, pixelformat="yuv420p", macro_block_size=1
    )

    for i in range(n):
        t = i / max(n - 1, 1)
        if t <= 0.55:
            u = ease_in_out(t / 0.55)
            sy = start_scroll + (end_scroll - start_scroll) * u
            await set_scroll(page, sy)
            # Recalculate hover after scroll so it tracks the component
            live = await resolve_target(page, selector, nth, None)
            mx = mx0 + (float(live["x"]) - mx0) * u
            my = my0 + (float(live["y"]) - my0) * u
            if i == 0 or i % 2 == 0:
                await apply_hover(page, selector, nth, mx, my)
        else:
            await set_scroll(page, end_scroll)
            live = await resolve_target(page, selector, nth, None)
            u = ease_in_out((t - 0.55) / 0.45)
            mx = mx0 + (float(live["x"]) - mx0) * (0.55 + 0.45 * u)  # continue toward target
            # actually already mostly there — lock to live
            mx, my = float(live["x"]), float(live["y"])
            if i == int(0.55 * n) or i % 3 == 0:
                await apply_hover(page, selector, nth, mx, my)

        png = await page.screenshot(type="png")
        img = Image.open(__import__("io").BytesIO(png)).convert("RGB")
        if img.size != (WIDTH, HEIGHT):
            img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        img = draw_caption(img, title)
        writer.append_data(np.array(img))

    writer.close()


async def main() -> None:
    from playwright.async_api import async_playwright

    ensure_dirs()

    # Flatten beats + synthesize audio first so durations drive motion
    flat: list[dict] = []
    for scene in SCENES:
        for bi, beat in enumerate(scene["beats"]):
            flat.append(
                {
                    "id": f"{scene['id']}_b{bi:02d}",
                    "scene": scene["id"],
                    "view": scene.get("view"),
                    "need_alert": scene.get("need_alert", False),
                    "title": scene["title"],
                    "text": beat["text"],
                    "selector": beat.get("selector"),
                    "nth": beat.get("nth", 0),
                    "scroll_ratio": beat.get("scroll_ratio"),
                }
            )

    print("Generating narration…")
    for item in flat:
        mp3 = AUDIO_DIR / f"{item['id']}.mp3"
        wav = AUDIO_DIR / f"{item['id']}.wav"
        dur = await synthesize(item["text"], mp3, wav)
        item["duration"] = dur + 0.25
        item["wav"] = str(wav)
        print(f"  {item['id']}: {item['duration']:.1f}s")

    print("Recording UI motion (smooth scroll + hover)…")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        await page.goto(BASE_URL, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(2800)

        await page.add_style_tag(
            content="""
            .nzcc-demo-hover {
              outline: 2px solid #3aa0ff !important;
              outline-offset: 3px !important;
              box-shadow: 0 0 0 5px rgba(58,160,255,0.22) !important;
              border-radius: 10px !important;
              transition: outline 0.2s ease, box-shadow 0.2s ease !important;
              position: relative;
              z-index: 5;
            }
            """
        )
        # Show notification badge for the demo
        await page.evaluate(
            """() => {
              const dot = document.getElementById('notify-dot');
              if (dot) dot.hidden = false;
            }"""
        )

        alert_ready = False
        current_view = None
        final_parts: list[Path] = []

        for item in flat:
            bid = item["id"]
            print(f"  recording {bid}…")
            silent = CLIPS_DIR / f"{bid}_silent.mp4"
            muxed = CLIPS_DIR / f"{bid}.mp4"

            if item["view"] is None:
                await record_title_clip(item["title"], item["duration"], silent)
            else:
                if item.get("need_alert") and not alert_ready:
                    await ensure_alert(page)
                    alert_ready = True
                    current_view = "alerts"

                if item["view"] != current_view:
                    await goto_view(page, item["view"])
                    current_view = item["view"]
                    await page.wait_for_timeout(500)
                    # reset scroll at page start
                    await set_scroll(page, 0)
                    await page.wait_for_timeout(200)

                await record_ui_beat(page, item, item["duration"], item["title"], silent)

            mux_av(silent, Path(item["wav"]), muxed)
            final_parts.append(muxed)

        await browser.close()

    print("Concatenating final MP4…")
    concat_videos(final_parts, FINAL_MP4)
    (OUT_DIR / "demo_meta.json").write_text(json.dumps(flat, indent=2), encoding="utf-8")
    print(f"Done: {FINAL_MP4}")
    print(f"Size: {FINAL_MP4.stat().st_size / (1024 * 1024):.1f} MB")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise
