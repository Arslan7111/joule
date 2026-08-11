# -*- coding: utf-8 -*-
"""Builds Joule_Coach_End_Product.pdf from verified repo state + strategy doc."""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable, ListFlowable, ListItem, KeepTogether, Frame, PageTemplate,
    BaseDocTemplate, NextPageTemplate
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas as canvas_mod

# ---- brand palette (from the strategy doc's own design direction) ----
CHARCOAL = colors.HexColor("#1c1f22")
WARMWHITE = colors.HexColor("#f4f2ee")
AMBER = colors.HexColor("#f5a623")
TEAL = colors.HexColor("#2a9d8f")
BRICK = colors.HexColor("#c0392b")
GREY = colors.HexColor("#5b6266")       # structural only: rules, dividers — never body text
TEXTGREY = colors.HexColor("#40474b")   # secondary text — kept high-contrast, not flat gray
LIGHTGREY = colors.HexColor("#e4e1da")

styles = getSampleStyleSheet()

def style(name, **kw):
    base = styles[kw.pop("base", "Normal")]
    s = ParagraphStyle(name, parent=base, **kw)
    styles.add(s)
    return s

TitleS = style("TitleS", fontName="Helvetica-Bold", fontSize=27, leading=29,
               textColor=CHARCOAL, spaceAfter=6)
KickerS = style("KickerS", fontName="Helvetica-Bold", fontSize=10, leading=12,
                textColor=AMBER, spaceAfter=10)
SubtitleS = style("SubtitleS", fontName="Helvetica", fontSize=12.5, leading=18,
                   textColor=TEXTGREY, spaceAfter=4)
H1 = style("H1", fontName="Helvetica-Bold", fontSize=17, leading=19,
           textColor=CHARCOAL, spaceBefore=18, spaceAfter=8)
H2 = style("H2", fontName="Helvetica-Bold", fontSize=13, leading=15,
           textColor=CHARCOAL, spaceBefore=12, spaceAfter=6)
H3 = style("H3", fontName="Helvetica-Bold", fontSize=10.8, leading=13,
           textColor=TEAL, spaceBefore=8, spaceAfter=4)
Body = style("Body", fontName="Helvetica", fontSize=9.6, leading=14.5,
             textColor=CHARCOAL, alignment=TA_JUSTIFY, spaceAfter=6)
BodyL = style("BodyL", base="Body", fontSize=10.6, leading=16)
Small = style("Small", fontName="Helvetica", fontSize=8.3, leading=11.5,
              textColor=TEXTGREY, spaceAfter=4)
Callout = style("Callout", base="Body", fontSize=9.6, leading=13.5,
                textColor=CHARCOAL, backColor=WARMWHITE, borderPadding=8,
                spaceBefore=6, spaceAfter=10)
Bullet = style("BulletS", base="Body", fontSize=9.6, leading=14, spaceAfter=3,
               alignment=TA_LEFT)
TblHead = ParagraphStyle("TblHead", fontName="Helvetica-Bold", fontSize=8.6,
                          leading=11, textColor=colors.white)
TblCell = ParagraphStyle("TblCell", fontName="Helvetica", fontSize=8.4,
                          leading=11.8, textColor=CHARCOAL)
TblCellB = ParagraphStyle("TblCellB", fontName="Helvetica-Bold", fontSize=8.4,
                           leading=11.8, textColor=CHARCOAL)
Caption = style("Caption", fontName="Helvetica-Oblique", fontSize=8.4,
                 leading=11, textColor=TEXTGREY, spaceBefore=2, spaceAfter=8)

def P(text, s=Body):
    return Paragraph(text, s)

def rule(color=LIGHTGREY, thickness=0.8, before=4, after=10):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                       spaceBefore=before, spaceAfter=after)

def bullets(items, s=Bullet, bullet_color=AMBER):
    flows = []
    for it in items:
        flows.append(ListItem(P(it, s), bulletColor=bullet_color, value='•'))
    return ListFlowable(flows, bulletType='bullet', leftIndent=14, spaceBefore=2, spaceAfter=8)

def tbl(header, rows, col_widths, header_bg=CHARCOAL):
    data = [[Paragraph(h, TblHead) for h in header]]
    for r in rows:
        data.append([Paragraph(str(c), TblCell) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), header_bg),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, WARMWHITE]),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHTGREY),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    return t

# ---------- page chrome ----------
PAGE_W, PAGE_H = LETTER

def draw_cover_bg(c, doc):
    c.saveState()
    c.setFillColor(CHARCOAL)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.rect(0, PAGE_H - 0.06*inch, PAGE_W, 0.06*inch, fill=1, stroke=0)
    c.rect(0, 0, PAGE_W, 0.06*inch, fill=1, stroke=0)
    c.restoreState()

def draw_header_footer(c, doc):
    c.saveState()
    c.setFont("Helvetica", 7.6)
    c.setFillColor(GREY)
    c.drawString(0.75*inch, PAGE_H - 0.55*inch, "JOULE COACH · END-PRODUCT SPECIFICATION")
    c.drawRightString(PAGE_W - 0.75*inch, PAGE_H - 0.55*inch, "github.com/Arslan7111/joule")
    c.setStrokeColor(LIGHTGREY)
    c.setLineWidth(0.6)
    c.line(0.75*inch, PAGE_H - 0.62*inch, PAGE_W - 0.75*inch, PAGE_H - 0.62*inch)
    c.setFont("Helvetica", 8)
    c.setFillColor(GREY)
    c.drawCentredString(PAGE_W/2, 0.5*inch, f"{doc.page}")
    c.setFillColor(AMBER)
    c.rect(0, 0, PAGE_W, 0.06*inch, fill=1, stroke=0)
    c.restoreState()

class CoverTemplate(PageTemplate):
    def __init__(self, id, frames):
        PageTemplate.__init__(self, id, frames, onPage=draw_cover_bg)

class BodyTemplate(PageTemplate):
    def __init__(self, id, frames):
        PageTemplate.__init__(self, id, frames, onPage=draw_header_footer)

def build():
    doc = BaseDocTemplate(
        "Joule_Coach_End_Product.pdf",
        pagesize=LETTER,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.85*inch, bottomMargin=0.75*inch,
        title="Joule Coach — The End Product",
        author="Joule",
    )
    cover_frame = Frame(0.75*inch, 0.75*inch, PAGE_W-1.5*inch, PAGE_H-1.6*inch, id='cover')
    body_frame = Frame(0.75*inch, 0.75*inch, PAGE_W-1.5*inch, PAGE_H-1.6*inch, id='body')
    doc.addPageTemplates([
        CoverTemplate('Cover', [cover_frame]),
        BodyTemplate('Body', [body_frame]),
    ])

    story = []

    # ================= COVER =================
    story.append(Spacer(1, 0.55*inch))
    story.append(P("JOULE · END-PRODUCT SPECIFICATION", ParagraphStyle(
        "coverKicker", fontName="Helvetica-Bold", fontSize=10.5, textColor=AMBER,
        spaceAfter=10)))
    story.append(P("Joule Coach", ParagraphStyle(
        "coverTitle", fontName="Helvetica-Bold", fontSize=34, leading=38,
        textColor=colors.white, spaceAfter=4)))
    story.append(P("What the finished product looks like — and what stands between\n"
                    "the validated engine on GitHub and that product today.",
                    ParagraphStyle("coverSub", fontName="Helvetica", fontSize=13,
                                   leading=18, textColor=WARMWHITE, spaceAfter=0)))
    story.append(Spacer(1, 0.95*inch))

    meta_rows = [
        ["Prepared", "10 August 2026"],
        ["Source repo", "github.com/Arslan7111/joule (private) — verified at commit de2a3e7"],
        ["Companion source", "Joule_Coach_Strategy.pdf — product spec + technical roadmap"],
        ["Method", "Every engine claim below was re-checked directly against the cloned"
                   " repository (src/config.py, src/dashboard.py, src/exercise_classifier.py,"
                   " src/reid.py, README.md, STATUS.md), not taken on the earlier document's word."],
        ["Status", "Descriptive target-state document. Sections marked ENGINE TODAY reflect"
                   " code that exists now; sections marked END PRODUCT describe what does not"
                   " exist yet and must be built."],
    ]
    mt = Table(meta_rows, colWidths=[1.3*inch, 4.7*inch])
    mt.setStyle(TableStyle([
        ('TEXTCOLOR', (0,0), (0,-1), AMBER),
        ('TEXTCOLOR', (1,0), (1,-1), WARMWHITE),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LINEBELOW', (0,0), (-1,-2), 0.4, GREY),
    ]))
    story.append(mt)
    story.append(NextPageTemplate('Body'))
    story.append(PageBreak())

    # ================= 1. WHAT THIS DOCUMENT IS =================
    story.append(P("1 · Reading this document", KickerS))
    story.append(P("How to use what follows", H1))
    story.append(P(
        "This is a description of <b>Joule Coach as a finished, shippable product</b> — the "
        "member app, the gym-floor hardware experience, the operator console, and the business "
        "wrapped around them — followed by a grounded account of the engineering distance between "
        "that end state and the code sitting in the repository today. It merges two sources: the "
        "product/technical planning already done in <i>Joule_Coach_Strategy.pdf</i>, and a fresh "
        "read of the actual <b>github.com/Arslan7111/joule</b> codebase (commit <b>de2a3e7</b>, "
        "~3,900 lines across <b>pipeline.py</b> and 18 modules in <b>src/</b>) to confirm nothing "
        "below overstates what exists.", BodyL))
    story.append(Callout([
        P("<b>Nothing described in Part A has been built as a product yet.</b> The pipeline that "
          "makes it possible — detection, tracking, pose, rep counting, form scoring, 3D fusion — "
          "is real, running code, already benchmarked against public datasets. The app, the "
          "backend, persistence, billing, and the compliance layer around it are not. Part B says "
          "precisely where that line sits.", Body)
    ][0].text, Callout) if False else None)
    # (Callout content built directly below instead of the odd list hack above)
    story[-1] = Table([[P(
        "<b>Nothing described in Part A has been built as a product yet.</b> The engine that makes "
        "it possible — detection, tracking, pose, rep counting, form scoring, 3D fusion — is real, "
        "running code, already benchmarked against public datasets (RepCount, CMU Panoptic, Fit3D). "
        "The app, backend, persistence, billing, and compliance layer around it are not. Part B "
        "states precisely where that line sits, file by file.", Body)]], colWidths=[6.0*inch])
    story[-1].setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), WARMWHITE),
        ('BOX', (0,0), (-1,-1), 0, colors.white),
        ('LINEBEFORE', (0,0), (0,-1), 3, AMBER),
        ('TOPPADDING', (0,0), (-1,-1), 10), ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12), ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(Spacer(1, 6))

    story.append(P("Document structure", H2))
    story.append(bullets([
        "<b>Part A — The end product.</b> Joule Coach as a member, a gym owner, and floor staff "
        "would actually experience it once fully built: the visit end to end, the full feature set, "
        "the app screen by screen, the real-time and gamified layer (points, streaks, badges), "
        "brand and design language, the business model, and the underlying system architecture.",
        "<b>Part B — Distance from today's engine.</b> A verified, file-by-file account of what "
        "exists in the repo right now versus what Part A requires, organized by the same phase "
        "structure (F–L) as the technical roadmap, so the gap is auditable rather than asserted.",
        "<b>Part C — What could still go wrong.</b> The honest risk list that determines what an "
        "early version of this product is actually allowed to promise a paying member.",
    ]))

    story.append(PageBreak())

    # ================= PART A HEADER =================
    story.append(P("PART A", KickerS))
    story.append(P("The End Product", ParagraphStyle("PartTitle", fontName="Helvetica-Bold",
                    fontSize=22, textColor=CHARCOAL, spaceAfter=6)))
    story.append(P("Joule Coach as a member, owner, and staff member would experience it once "
                    "fully built — the product Part B has to earn.", SubtitleS))
    story.append(rule(color=AMBER, thickness=1.6, before=8, after=14))

    # ---- A1 One-paragraph pitch ----
    story.append(P("A.1 · The pitch", KickerS))
    story.append(P("What Joule Coach is", H1))
    story.append(P(
        "Joule Coach turns a gym's existing ceiling cameras into a personal trainer that never "
        "clocks out. A member checks in with a badge tap, trains as normal, and within seconds of "
        "finishing a set sees an honest read of what they did — how many reps, how deep, how "
        "controlled, and the one or two things to fix next time — without a phone held up, a "
        "wearable, or a human standing over them. Their plan for the week lives in the app; whether "
        "they actually did it is measured, not self-reported. For the gym, it is a premium tier "
        "members will pay more for, sold and operated without hiring more coaching staff.", BodyL))
    story.append(P(
        "What makes this credible rather than another AI-fitness pitch: the computer-vision engine "
        "underneath it is not a mockup. It already detects people, tracks them, estimates 3D pose "
        "from multiple synchronized cameras, counts reps with a per-person adaptive state machine, "
        "and scores form — and every one of those components has already been benchmarked against "
        "public research datasets (RepCount, CMU Panoptic, Fit3D), not just demoed on a clean solo "
        "video. Part B documents exactly how far that engine already reaches, and where the product "
        "wrapped around it still needs to be built.", BodyL))

    # ---- A2 The visit, end to end ----
    story.append(P("A.2 · The member experience", KickerS))
    story.append(P("A visit, start to finish", H1))

    visit_steps = [
        ("01 · Check in", "A quick badge tap or QR scan at a wall-mounted kiosk near the entrance. "
         "No phone required to start. The kiosk confirms the member's identity is bound to today's "
         "visit within about three seconds; if it can't confidently match, a staff member resolves "
         "it in two taps rather than the app silently guessing."),
        ("02 · Pick the movement", "Before a set, the member picks their exercise from a short list "
         "on their phone — squat, deadlift, curl, row, overhead press, lateral raise at launch. "
         "Anything the system can't yet score (sit-ups, head-on bench press, anything near a mirror) "
         "is visibly marked \"coming soon,\" never hidden and never silently mis-scored."),
        ("03 · Train, with one glanceable cue", "During the set the phone (held or set on a bench) "
         "shows just a rep counter and a single light/tone cue if the member drifts out of the "
         "camera's frame. No busy live overlay competing for attention mid-lift — that is a "
         "deliberate choice, not a missing feature (see A.5)."),
        ("04 · The report, seconds later", "Within a handful of seconds of racking the weight, a "
         "report slides up: rep count, per-rep depth validity, a plain-language form read, and the "
         "one or two biggest deviations to fix — \"knees tracking inward on reps 4–6.\" Every report "
         "states outright whether it came from a 3D fused read (higher confidence) or a single "
         "camera (lower), shown as a visual language, not a hedge buried in copy."),
        ("05 · The week, tracked honestly", "The plan the member built lives in the app; adherence is "
         "measured against what the cameras actually saw, not what the member says they did. A "
         "\"planned vs. done\" view distinguishes a genuinely skipped set from a set the cameras "
         "simply couldn't see — a camera outage or an uncovered machine is never reported as a "
         "missed workout."),
        ("06 · Progress that compounds", "Trend charts across weeks and months — form-score "
         "trajectory, joint-angle history, streaks — framed simply for a first-timer and exposed as "
         "raw, exportable data for a member who wants it."),
    ]
    for title, body in visit_steps:
        row = Table([[P(title, ParagraphStyle("stepTitle", fontName="Helvetica-Bold", fontSize=10.2,
                        textColor=TEAL)), P(body, Body)]], colWidths=[1.35*inch, 4.65*inch])
        row.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (0,-1), 0),
        ]))
        story.append(row)
    story.append(Spacer(1, 6))

    # ---- A3 Feature set ----
    story.append(P("A.3 · The complete feature set", KickerS))
    story.append(P("What ships, for whom", H1))
    story.append(P(
        "The strategy document staged this across MVP → V1 → V2+ sprints; collapsed into the "
        "finished product, this is the full surface Joule Coach presents once mature.", Body))

    story.append(P("For the member", H2))
    story.append(tbl(
        ["Feature", "What it does"],
        [
            ["Badge/QR check-in", "Binds a member's identity to a fresh visit at a fixed kiosk camera; failed matches route to a two-tap staff override, never a silent misattribution."],
            ["Guided session start", "Closed exercise picker scoped to what the engine can currently score; unsupported movements are labeled, not hidden."],
            ["Post-set form report", "Rep count, per-rep validity, plain-language form score with 1–2 deviation cues, and an explicit 3D-vs-2D confidence label on every report."],
            ["Stay-in-frame cue", "A low-latency light/tone signal, independent of and faster than the scoring pipeline, when the member's feet or body leave the calibrated volume."],
            ["Plan builder", "Weekly plan assembled from a supported-exercise library; blocks adding a movement the member's home gym has no camera coverage for."],
            ["Verified adherence", "Cross-references the plan against actually-detected sessions — distinguishes \"not detected\" (camera/coverage issue) from \"detected but under-volume,\" and only the latter may ever read as a missed workout."],
            ["Progress dashboard", "Multi-session trend charts, persona-adaptive: a simple monthly summary by default, a raw per-joint-angle export mode for advanced members."],
            ["Video library", "Reference-vs-common-mistake clips mapped 1:1 to exercises the live system actually scores — never a demo for a movement the tracker can't confirm."],
            ["Injury-risk trend cards", "Fatigue, ROM degradation, tempo collapse, and asymmetry surfaced as directional trend cards, not a diagnosis — sustained flags route to a human reviewer."],
            ["Reminders", "Session and plan nudges that never assert a missed session with more confidence than the underlying detection actually has."],
        ],
        [1.7*inch, 4.3*inch]
    ))
    story.append(Spacer(1, 8))

    story.append(P("For the gym owner and floor staff", H2))
    story.append(tbl(
        ["Feature", "What it does"],
        [
            ["Operator console", "Camera/station health (last-frame timestamp, calibration-drift warning), member roster, today's session volume; a camera dark for 2+ minutes pages staff."],
            ["Usage & business analytics", "Station utilization by hour, adherence rates across the membership, churn-risk flags — the number a gym owner actually renews on."],
            ["Staff exception panel", "Today's failed check-ins, dark cameras, ambiguous identity matches — the human backstop made concrete, not a support-ticket queue."],
            ["Install compliance tooling", "A guided camera-placement checklist tied to the engine's known blind spots (mirrors, feet-in-frame) with a live warning if a station's frame includes an uncalibrated reflective surface."],
            ["Subscription tier gating", "Base vs. premium (adds human-reviewer escalation and deeper analytics) — gates feature visibility, never gates how honest a report is."],
        ],
        [1.7*inch, 4.3*inch]
    ))
    story.append(Spacer(1, 8))

    story.append(P("The human backstop: Remote Coach", H2))
    story.append(P(
        "The one deliberately-added role that keeps the \"no human trainer needed\" promise honest "
        "rather than reckless: a lightweight remote reviewer queue for the small fraction of cases "
        "that genuinely need a person — ambiguous form calls, injury-risk escalations, premium "
        "plan customization. It converts the engine's real, named blind spots (bench press needs a "
        "side camera, mirrors are unreadable, sit-ups aren't counted yet) into a monetizable premium "
        "feature instead of a silent failure the member discovers on their own.", Body))

    story.append(PageBreak())

    # ---- A4 The app in your pocket ----
    story.append(P("A.4 · The app in your pocket", KickerS))
    story.append(P("Screen by screen", H1))
    story.append(P(
        "The member app is the daily surface for all of the above. Six screens carry almost the "
        "entire experience:", Body))

    app_screens = [
        ("Today", "The home screen: today's planned session pulled from the member's plan, current "
         "check-in state, and a compact snapshot of level, streak, and points — enough to glance at "
         "on the way into the gym, nothing that demands attention."),
        ("Live Session", "Opened once a set starts. Large, glanceable rep counter; the stay-in-frame "
         "cue; and — new in this layer — points ticking up in real time as each rep is confirmed "
         "(see A.5). No live form-correction overlay here by design; that arrives post-set."),
        ("Post-Set Report", "Slides up automatically once the set ends: the skeleton overlay for the "
         "set's worst rep, plain-language form read, 1–2 corrective cues, and any bonus points/badge "
         "progress earned from clean-form reps in that set."),
        ("Plan Builder", "A calendar-week grid assembled from the supported-exercise library; each "
         "card shows its own confidence/coverage badge so a member never plans around a movement the "
         "gym can't track."),
        ("Progress & Achievements", "Trend charts (form-score trajectory, joint-angle history) sit "
         "alongside the gamified layer — level, badge case, streak calendar, and an opt-in gym "
         "leaderboard (A.5)."),
        ("Video Library", "Reference-vs-common-mistake clips, one per supported exercise, deep-linked "
         "straight from a report's corrective cue."),
    ]
    for title, body in app_screens:
        row = Table([[P(title, ParagraphStyle("screenTitle", fontName="Helvetica-Bold", fontSize=10.2,
                        textColor=TEAL)), P(body, Body)]], colWidths=[1.35*inch, 4.65*inch])
        row.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (0,-1), 0),
        ]))
        story.append(row)
    story.append(Spacer(1, 6))

    # ---- A5 Gamification & real-time feedback ----
    story.append(P("A.5 · Real-time feedback and the gamified layer", KickerS))
    story.append(P("Points, streaks, and what \"live\" honestly means", H1))
    story.append(P(
        "Two different things get called \"real-time\" in a product like this, and the end product "
        "keeps them clearly separated rather than blurring them into one marketing claim.", BodyL))

    rt_rows = [
        ["Live rep & points feedback", "AVAILABLE NOW",
         "The rep-counting state machine already counts a rep the instant it completes — it's how "
         "the engine works today, confirmed in src/state_machine.py and already streamed live over "
         "the existing /data endpoint. Gamifying that stream (a live rep counter, a points tick, a "
         "streak pulse) is a UI layer on top of something the engine genuinely does in real time — "
         "not a promise ahead of the technology."],
        ["Live corrective form feedback", "GATED",
         "A mid-rep overlay that tells a member \"straighten your back\" while they're still in the "
         "rep is a different, much harder claim — it needs the full pose→angle→form pipeline running "
         "at rep speed with a proven latency budget on real hardware. That validation work is "
         "Phase E/H in Part B and has not run yet. Until it has, corrective feedback stays post-set, "
         "seconds after the rep — still faster and more specific than a human trainer glancing over "
         "occasionally, just not mid-rep."],
    ]
    story.append(tbl(["Layer", "Status", "What's actually true"], rt_rows, [1.5*inch, 0.85*inch, 3.65*inch]))
    story.append(Spacer(1, 8))

    story.append(P("The points system", H2))
    story.append(P(
        "Points are earned only from camera-confirmed activity — the same evidentiary standard as "
        "adherence tracking (A.3): nothing is awarded from a self-reported set, and nothing is ever "
        "deducted for a session the cameras simply didn't see.", Body))
    story.append(tbl(
        ["Action", "Points", "Basis"],
        [
            ["Rep completed", "+1", "Live, the instant the state machine confirms it — no waiting on form scoring."],
            ["Clean-form rep (in the top confidence band)", "+3 bonus", "Applied retroactively once the post-set form score computes; only on a 3D-fused, high-confidence read."],
            ["Full planned set completed", "+10", "Requires the prescribed reps observed, not just attempted."],
            ["Weekly plan fully completed", "+50", "Same four-state observability model as adherence — only an observed-complete week counts."],
            ["Consecutive-day streak", "Multiplier, no cap on the downside", "Streaks add a multiplier on top of points earned; a missed or unobservable day pauses the multiplier — it is never reset to zero and never triggers a guilt notification."],
        ],
        [1.9*inch, 1.0*inch, 3.1*inch]
    ))
    story.append(Spacer(1, 6))

    story.append(P("Levels, badges, and the leaderboard", H2))
    story.append(bullets([
        "<b>Per-exercise levels</b> (e.g. Bronze/Silver/Gold Squat) are earned from a rolling trend "
        "in consistency and volume, never from a single rep or a single lucky high-confidence "
        "read — the same anti-fake-precision principle that governs the form score itself.",
        "<b>Badges</b> are milestone-based and independently verifiable (\"100 tracked squats,\" "
        "\"4-week streak\") and, like every other number in this product, only count what the "
        "cameras actually observed.",
        "<b>Leaderboard</b> is opt-in and gym-local by default, ranked on consistency/streak rather "
        "than raw weight moved, so it can't quietly push someone toward an unsafe attempt to climb "
        "it. A gym can disable it entirely for its floor.",
    ], bullet_color=AMBER))
    story.append(Callout)
    story[-1] = Table([[P(
        "<b>The one rule that doesn't bend for gamification:</b> every anti-pattern already set for "
        "the rest of the product applies here too — no streak-shaming, no guilt notifications for a "
        "missed or unobservable session, no fake precision in how a point or badge is earned. Points "
        "make honest tracking more satisfying to look at; they don't get to lower the bar for what "
        "counts as \"observed.\"", Body)]], colWidths=[6.0*inch])
    story[-1].setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), WARMWHITE),
        ('LINEBEFORE', (0,0), (0,-1), 3, BRICK),
        ('TOPPADDING', (0,0), (-1,-1), 10), ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12), ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))

    story.append(PageBreak())

    # ---- A6 Design language ----
    story.append(P("A.6 · Look and feel", KickerS))
    story.append(P("Design language", H1))
    story.append(P(
        "\"Calibrated confidence, not hype.\" The single biggest design risk this product carries "
        "is overclaiming certainty it doesn't have — a member told \"perfect form!\" on a rep the "
        "system was actually unsure about, who then gets hurt, is the failure mode that kills the "
        "business. Every score, count, or alert carries a visible, low-friction confidence signal: "
        "solid outline for a high-confidence 3D fused read, dashed for a single-camera 2D estimate, "
        "greyed for insufficient data. The voice is a sharp, honest strength coach, not a gamified "
        "fitness app — direct and occasionally warm, never cutesy about safety, and never guilt-"
        "shaming a missed session.", Body))

    swatch_data = [
        [Table([[""]], colWidths=[0.32*inch], rowHeights=[0.22*inch],
               style=TableStyle([('BACKGROUND',(0,0),(-1,-1),CHARCOAL)])),
         "Charcoal #1c1f22", "Dark surface base"],
        [Table([[""]], colWidths=[0.32*inch], rowHeights=[0.22*inch],
               style=TableStyle([('BACKGROUND',(0,0),(-1,-1),WARMWHITE),('BOX',(0,0),(-1,-1),0.5,LIGHTGREY)])),
         "Warm white #f4f2ee", "Light surface base"],
        [Table([[""]], colWidths=[0.32*inch], rowHeights=[0.22*inch],
               style=TableStyle([('BACKGROUND',(0,0),(-1,-1),AMBER)])),
         "Amber #f5a623", "Actionable coaching cues & alerts only"],
        [Table([[""]], colWidths=[0.32*inch], rowHeights=[0.22*inch],
               style=TableStyle([('BACKGROUND',(0,0),(-1,-1),TEAL)])),
         "Teal #2a9d8f", "\"Confirmed good\" high-confidence states only"],
        [Table([[""]], colWidths=[0.32*inch], rowHeights=[0.22*inch],
               style=TableStyle([('BACKGROUND',(0,0),(-1,-1),BRICK)])),
         "Brick red #c0392b", "Risk/injury alerts — restrained, never neon"],
    ]
    swt = Table([[r[0], P(r[1], TblCellB), P(r[2], TblCell)] for r in swatch_data],
                colWidths=[0.5*inch, 1.6*inch, 3.9*inch])
    swt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                              ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(swt)
    story.append(Spacer(1, 8))
    story.append(bullets([
        "<b>Typography:</b> a workhorse grotesque with tabular figures for every metric and table; a more characterful display face for headlines and coaching-voice moments.",
        "<b>Layout:</b> dense, data-forward for the progress view and operator console; airy, single-focus screens for in-the-moment gym-floor flows (check-in, post-set report).",
        "<b>Signature element:</b> the real skeleton/joint-angle overlay — derived from actual pose data, not a generic icon — used throughout as the app's visual identity. It's the one piece of branding a copycat can't fake, because it's literally the product's own output.",
        "<b>Anti-patterns:</b> no fake precision (\"form score: 94.7%\" where the error band doesn't support it — round to bands or tiers instead); no stock-photo gym imagery or SaaS gradient-mesh hero sections; no streak-shaming.",
    ]))

    story.append(PageBreak())

    # ---- A7 Business model ----
    story.append(P("A.7 · The business", KickerS))
    story.append(P("How Joule Coach makes money", H1))
    story.append(P(
        "Two-sided subscription: gyms pay per site (camera install + a per-camera or per-member "
        "fee) to offer the product as a premium tier; members pay a subscription — either bundled "
        "into gym membership or billed directly — for the app, with a Remote Coach add-on as the "
        "premium upsell. The real commercial test is not the engine's benchmark accuracy; it's "
        "whether a pilot gym's member retention measurably beats its own historical baseline, and "
        "whether a second, independently-sourced gym signs on without a founder in the room.", BodyL))
    story.append(tbl(
        ["What it tracks", "Why it's the real test"],
        [
            ["60/90-day member retention vs. the gym's own historical baseline", "The actual business case — not engagement in isolation, the delta."],
            ["Gym owner renewal after the pilot, then a second independently-sourced gym", "The second sale is the test of whether this generalizes past one hand-tuned install."],
            ["False-\"missed\"-session rate in adherence tracking", "The costlier error direction — must stay near zero or it reads as accusing paying members."],
            ["Per-site unit economics (install cost amortized against subscription revenue)", "Depends directly on the unmeasured edge-hardware throughput question in Part B."],
        ],
        [2.6*inch, 3.4*inch]
    ))

    # ---- A8 System shape ----
    story.append(P("A.8 · How it's built", KickerS))
    story.append(P("System architecture", H1))
    story.append(P(
        "Three tiers, with a deliberate boundary: raw video never leaves the gym.", Body))

    arch_rows = [
        ["EDGE — one device per gym site", "Runs inference on-site: camera ingest, detection, pose, "
         "per-person analysis (rep counting, form, risk), and the visit-scoped identity gallery. "
         "Emits only events and skeleton data outward — never raw frames."],
        ["CONTROL PLANE — cloud, multi-tenant", "Authenticated ingest and core APIs, tenant-scoped "
         "storage (a small, hot relational store for members/visits/reps distinct from a large, cold "
         "store for raw angle series), the plan/adherence engine, billing, notifications, and the "
         "exercise-video catalog."],
        ["APPS — member, operator, content", "The member phone app, the gym operator console, and a "
         "CDN-delivered video library, all reading from the control plane's APIs."],
    ]
    for title, body in arch_rows:
        row = Table([[P(title, ParagraphStyle("archTitle", fontName="Helvetica-Bold", fontSize=9.6,
                        textColor=colors.white, backColor=CHARCOAL, borderPadding=6))]],
                    colWidths=[6.0*inch])
        story.append(row)
        story.append(Spacer(1, 3))
        story.append(P(body, Body))
        story.append(Spacer(1, 4))

    story.append(Callout)
    story[-1] = Table([[P(
        "<b>Why edge, not cloud, for inference:</b> it keeps the compliance surface small (the cloud "
        "never holds video of anyone's body), avoids a sustained multi-tens-of-Mbps upload commitment "
        "per site running 12+ hours a day, and means a gym with a flaky internet connection still "
        "tracks workouts and syncs later instead of going dark. This is treated as close to "
        "irreversible once built around.", Body)]], colWidths=[6.0*inch])
    story[-1].setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), WARMWHITE),
        ('LINEBEFORE', (0,0), (0,-1), 3, TEAL),
        ('TOPPADDING', (0,0), (-1,-1), 10), ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12), ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))

    story.append(P("Identity, done honestly", H2))
    story.append(P(
        "The end product never persists what a member looks like. A short-lived visit-scoped "
        "appearance match (built from clothing colour and generic features, good for maybe 30 "
        "minutes) links tracked bodies together during one visit; a durable member_id, established "
        "only by an authenticated check-in, is what survives between visits. No appearance template "
        "is ever stored — the single most consequential architectural commitment in the whole "
        "product, covered in depth in Part B.4.", Body))

    story.append(PageBreak())

    # ================= PART B =================
    story.append(P("PART B", KickerS))
    story.append(P("Distance From Today's Engine", ParagraphStyle("PartTitle2", fontName="Helvetica-Bold",
                    fontSize=22, textColor=CHARCOAL, spaceAfter=6)))
    story.append(P("What is verified, running code in github.com/Arslan7111/joule right now, "
                    "versus what Part A requires — checked directly against the repository, "
                    "commit de2a3e7.", SubtitleS))
    story.append(rule(color=TEAL, thickness=1.6, before=8, after=14))

    story.append(P("B.1 · Verified engine snapshot", KickerS))
    story.append(P("What actually runs today", H1))
    story.append(P(
        "pipeline.py is a command-line tool, not a service: it builds one camera-processing thread "
        "per source, runs until the clip or feed ends, and writes a single JSON file on exit. "
        "Re-confirmed directly in the repo for this document:", Body))

    verified_rows = [
        ["Detector / tracker", "YOLOv8n (src/config.py: DETECTOR_MODEL='yolov8n.pt', DETECTOR_CONF=0.5) + ByteTrack."],
        ["Pose", "MediaPipe, top-down, one call per detected person per frame (cost scales linearly with people in frame)."],
        ["Rep counting", "Exactly two signals: knee average and elbow average. src/exercise_classifier.py's CLASS_FAMILY maps 'situp' and 'cardio' to family 'none' — confirmed still zero reps by design."],
        ["Exercise classes", "12 labels defined; per README/STATUS the trained model reliably emits a working subset — hinge/lunge/curl/row remain heuristic-only, not trained-model output."],
        ["Identity", "src/reid.py: MobileNetV3-small ImageNet features + an HSV clothing histogram (_DEEP_WEIGHT=0.6) — confirmed not a Re-ID-trained model. src/config.py: REID_STALE_SECONDS=1800 (30 min)."],
        ["Persistence", "None. SessionGallery is an in-memory dict rebuilt on every run; one JSON write at process exit; a second run into the same output directory overwrites the first."],
        ["HTTP surface", "src/dashboard.py: unauthenticated http.server on 0.0.0.0, default port 5000 (confirmed — README's documented port 8080 is stale). Routes confirmed live: /, /snapshot/<cam>, /data, /people, /checkin (a state-mutating GET, no auth)."],
        ["Validation record", "RepCount Part-A (MAE 0.742, OBO 22.4% aggregate), CMU Panoptic (3.7°–6.1° mean joint-angle error), Fit3D (5–7° for standing exercises, up to 13.3° for squat/pushup) — all confirmed in STATUS.md as already-run, published-dataset benchmarks."],
        ["What's absent", "Confirmed: no database, no web framework beyond http.server, no tests/ directory, no CI, no Dockerfile, no per-site configuration mechanism."],
    ]
    story.append(tbl(["Component", "Verified state (commit de2a3e7)"], verified_rows, [1.5*inch, 4.5*inch]))

    story.append(P("Read plainly: the perception engine is real and independently validated. "
                    "Everything Part A needs to turn that into a product — persistence, identity "
                    "that survives a restart, an authenticated API, an app, a business layer — "
                    "does not exist in the repository yet.", Body))

    story.append(PageBreak())

    story.append(P("B.2 · The four gaps that decide whether this is a product", KickerS))
    story.append(P("The hard problems, not the busywork", H1))
    story.append(tbl(
        ["Gap", "Size", "Why it's the hard one"],
        [
            ["Real-gym accuracy under crowding, occlusion, mirrors", "Unknown",
             "Never tested on real gym footage. The one adverse data point in the repo: the shipped detector caught both people only 30% of the time on heavily-occluded two-person footage (src/config.py benchmark notes)."],
            ["Throughput on affordable edge hardware", "Unknown",
             "Measured today: ~0.22s/frame for 4 fused views with one person, on a laptop. Pose cost is linear in people. Jetson numbers do not exist yet."],
            ["Identity that holds for a full visit on a busy floor", "Large",
             "Not \"persist the gallery\" — the embedding is clothing-dominated and won't match the same person next week. The real problem is holding one check-in-established binding through 90 minutes, equipment occlusion, and dozens of similarly-dressed people."],
            ["Privacy, consent, biometric-regulation compliance", "Large, non-negotiable",
             "The system is legally clean today only because it persists nothing. Every fix above (durable identity, historical storage) actively removes that property — this is the one gap where doing the engineering work creates the legal exposure."],
        ],
        [1.85*inch, 0.65*inch, 4.0*inch]
    ))

    story.append(P("B.3 · Path from here, phase by phase", KickerS))
    story.append(P("The build sequence", H1))
    story.append(P(
        "Condensed from the technical roadmap's Phase F–L structure, sequenced so nothing "
        "irreplaceable — a pilot gym's goodwill, its members' trust — is spent on a foreseeable "
        "failure.", Body))

    phase_rows = [
        ["F", "Persistence & identity spine", "Wall-clock time, durable session/visit/member records, an append-only event stream replacing \"one JSON at exit,\" bounded memory, and the identity-binding model itself — no gym or real footage required, can start today."],
        ["G", "Privacy & compliance gate", "Consent lifecycle, retention/deletion enforced and tested, access audit, and killing the unauthenticated dashboard outright. Hard gate: no real member's body may be processed commercially before this lands."],
        ["H", "Always-on floor runtime", "Turns the CLI script into a supervised service: RTSP timestamp sync, a measured (not estimated) Jetson throughput number, back-pressure policy, per-site configuration."],
        ["I", "Backend API + operator console + first pilot gym", "Authenticated APIs, check-in as the identity anchor, and the single most important deliverable of the whole roadmap — a human-ground-truth accuracy audit that produces the number marketing is actually allowed to use."],
        ["J", "Member app: plans, adherence, content", "The founder's product vision made real, built only once I's accuracy numbers exist — building this earlier risks designing a feature the engine can't honestly support."],
        ["K", "Multi-tenant scale-out", "Gyms two through N: true tenant isolation, billing, fleet operations, a self-serve site-commissioning workflow."],
        ["L", "Model & coverage expansion", "Continuous, parallel track: hip-driven rep counting (unlocks sit-ups), wider trained-class coverage, reference-based absolute form scoring, mirror dead-zone masking."],
    ]
    story.append(tbl(["Phase", "Goal", "What it delivers"], phase_rows, [0.4*inch, 1.7*inch, 4.4*inch]))

    story.append(PageBreak())

    story.append(P("B.4 · The one architectural decision that can't be undone", KickerS))
    story.append(P("Identity: bind at check-in, never persist appearance", H1))
    story.append(P(
        "This is called out on its own because getting it wrong is not fixable after the fact. "
        "The temptation, once a product needs to recognize returning members, will be to \"just "
        "save the gallery.\" Confirmed directly from src/reid.py and src/session.py: the embedding "
        "is generic ImageNet features plus a clothing-colour histogram, explicitly built around "
        "clothing staying constant within one session — it will not reliably match the same person "
        "wearing different clothes next Tuesday. Persisting it anyway would be both technically "
        "weak and, because a stored appearance template derived from someone's body is the textbook "
        "definition of a regulated biometric identifier (BIPA, GDPR Art. 9), the most expensive "
        "mistake available in this roadmap.", BodyL))
    story.append(P(
        "The end product instead keeps three layers strictly separate: a tracklet (seconds, "
        "never persisted), a visit-scoped person (one visit, RAM only, never persisted), and a "
        "member (forever, but only an ID and a binding record — never body data — created by an "
        "authenticated check-in event, not by appearance matching).", Body))

    story.append(PageBreak())

    story.append(P("PART C", KickerS))
    story.append(P("What Could Still Go Wrong", ParagraphStyle("PartTitle3", fontName="Helvetica-Bold",
                    fontSize=22, textColor=CHARCOAL, spaceAfter=6)))
    story.append(P("The honest risk list that determines what an early version of this product "
                    "is actually allowed to promise a paying member.", SubtitleS))
    story.append(rule(color=BRICK, thickness=1.6, before=8, after=14))

    story.append(P("C.1 · Full risk register", KickerS))
    story.append(P("Four categories, plainly stated", H1))
    risk_rows = [
        ["Accuracy", "Rep-count accuracy is not yet a product number (only benchmarked on public datasets, not real gym floors); bench press can't be reliably counted head-on; sit-ups count zero by design; mirrors are a total, unclosable blind spot in a typically mirror-walled gym; feet-out-of-frame degrades silently, not with an error."],
        ["Identity & trust", "Mis-attribution is the system's own documented \"worst failure mode\" — as a product it becomes a billing dispute, not just a data error; conservative matching produces fragmentation that looks like data loss; bystanders (staff, guests, minors) are currently enrolled with no consent model."],
        ["Platform & legal", "The current HTTP dashboard is a live, unauthenticated video feed of the gym floor to anyone on the network; BIPA's private right of action is the single highest-cost legal exposure in the US; a bumped camera silently invalidates calibration with no automatic detection today."],
        ["Commercial", "Per-site unit economics are unknown until real edge-hardware throughput is measured; the shipped detector (Ultralytics YOLOv8) is AGPL-licensed and needs a commercial-license decision before anything ships."],
    ]
    story.append(tbl(["Category", "What could go wrong"], risk_rows, [1.3*inch, 4.7*inch]))

    story.append(P("What an early version can honestly promise", H2))
    story.append(bullets([
        "Automatic counting of squats and knee-driven lower-body work, elbow-driven upper-body work, at properly placed, mirror-free, feet-in-frame stations — subject to a real ground-truth accuracy audit at the pilot site.",
        "Per-set consistency and control feedback with actionable coaching cues, and true 3D joint angles at 3+ camera fused stations.",
        "A plan builder and adherence tracking for observed activity, with transparent self-logging for everything cameras can't see.",
    ], bullet_color=TEAL))
    story.append(P("What it must not promise until the engineering work above closes the gap", H2))
    story.append(bullets([
        "Reliable bench-press counting without a true side camera, or any sit-up/core-flexion counting.",
        "Coverage of mirror-adjacent areas, or an absolute \"correctness %\" before reference-signature scoring is validated.",
        "Injury prediction or any medical claim — risk signals are training-load indicators, nothing more.",
        "Adherence assertions about activity the system genuinely could not observe.",
    ], bullet_color=BRICK))

    story.append(rule(before=14, after=8))
    story.append(P(
        "Sources: Joule_Coach_Strategy.pdf (product spec + technical roadmap, prepared 6 Aug 2026) "
        "and a direct read of github.com/Arslan7111/joule at commit de2a3e7 — README.md, STATUS.md, "
        "ROADMAP.md, DEVELOPMENT.md, CAMERA_PLACEMENT.md, pipeline.py, and src/config.py, "
        "src/dashboard.py, src/reid.py, src/session.py, src/exercise_classifier.py, "
        "src/output.py. Compiled 10 August 2026.", Small))

    doc.build(story)

if __name__ == "__main__":
    build()
