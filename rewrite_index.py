import sys

# Read backup with correct encoding
with open('index_backup.py', 'r', encoding='utf-16-le') as f:
    code = f.read()

# 1. max_num_hands = 2
code = code.replace(
    'hands = mp_hands.Hands(max_num_hands=1,',
    'hands = mp_hands.Hands(max_num_hands=2,'
)

# 2. Start in MAIN_MENU
code = code.replace(
    'MODES         = ["GRID","AIR","ASL","ASSIST","MEMO"]',
    'MODES         = ["GRID","AIR","ASL","ASSIST","MEMO","MAIN_MENU"]'
)
code = code.replace('input_mode    = "GRID"', 'input_mode    = "MAIN_MENU"')
code = code.replace('last_vol_y    = None', 'last_vol_y    = None\n    escape_start  = 0.0')

# 3. Inject new UI helpers before the Keyboard Renderer section
# Use plain text search to avoid unicode box-drawing char issues
MARKER = 'Keyboard Renderer'
INJECT = '''
# ────────────────── Welcome Screen & Navigation ──────────────────────────────────────────────────────────
def _pill(frame, x, y, w, h, color, filled=True, radius=10):
    """Draw a rounded rect (pill shape)."""
    import cv2, numpy as np
    overlay = frame.copy()
    cv2.rectangle(overlay, (x + radius, y), (x + w - radius, y + h), color, -1)
    cv2.rectangle(overlay, (x, y + radius), (x + w, y + h - radius), color, -1)
    for cx, cy in [(x+radius,y+radius),(x+w-radius,y+radius),(x+radius,y+h-radius),(x+w-radius,y+h-radius)]:
        cv2.circle(overlay, (cx, cy), radius, color, -1)
    cv2.addWeighted(overlay, 1.0, frame, 0.0, 0, frame)
    if not filled:
        cv2.rectangle(frame, (x,y), (x+w,y+h), color, 2)


def draw_main_menu(frame, hover_key, progress):
    """Portfolio-style dark welcome screen."""
    import cv2, numpy as np
    button_list = []
    fh, fw = frame.shape[:2]

    # Solid black background
    frame[:] = (0, 0, 0)

    # ── Header text ─────────────────────────────────────────────
    # "HI, I'M" — bold white, filled
    cv2.putText(frame, "HI, I'M", (80, 160),
                cv2.FONT_HERSHEY_DUPLEX, 3.5, (255,255,255), 12, cv2.LINE_AA)
    # "SIMRA FAISAL" — outline / stroke style (draw twice: thick dark then thin white)
    cv2.putText(frame, "SIMRA FAISAL", (80, 280),
                cv2.FONT_HERSHEY_DUPLEX, 4.0, (255,255,255), 16, cv2.LINE_AA)
    cv2.putText(frame, "SIMRA FAISAL", (80, 280),
                cv2.FONT_HERSHEY_DUPLEX, 4.0, (0,0,0), 2, cv2.LINE_AA)

    # Pink accent label  "AI COMMUNICATION SYSTEM"
    PINK = (180, 80, 180)
    cv2.putText(frame, "AI COMMUNICATION SYSTEM", (80, 360),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, PINK, 3, cv2.LINE_AA)

    # Description
    cv2.putText(frame, "Hover over a mode to get started.", (80, 430),
                cv2.FONT_HERSHEY_SIMPLEX, 0.95, (200,200,200), 2, cv2.LINE_AA)

    # ── Mode buttons (row layout) ────────────────────────────────
    modes = [
        ("GRID",   "ON-SCREEN\nKEYBOARD",  (180, 80, 180),  True ),
        ("ASL",    "ASL\nTRANSLATOR",      (255,255,255),   False),
        ("AIR",    "AIR\nHAND-WRITING",    (255,255,255),   False),
        ("ASSIST", "COGNITIVE\nASSISTANCE",(255,255,255),   False),
    ]

    bw, bh = 230, 90
    gap   = 30
    total = len(modes) * bw + (len(modes)-1) * gap
    sx    = (fw - total) // 2
    sy    = 520

    for i, (mid, label, col, filled) in enumerate(modes):
        x = sx + i * (bw + gap)
        hovered = hover_key and hover_key[0] == mid

        bg_col = col if filled else (0,0,0)
        bd_col = col

        # Fill rectangle
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, sy), (x+bw, sy+bh), bg_col, -1)
        cv2.addWeighted(overlay, 1.0, frame, 0.0, 0, frame)
        cv2.rectangle(frame, (x, sy), (x+bw, sy+bh), bd_col, 2)

        if hovered:
            # Highlight
            ov2 = frame.copy()
            cv2.rectangle(ov2, (x, sy), (x+bw, sy+bh), (255,255,255), -1)
            cv2.addWeighted(ov2, 0.15, frame, 0.85, 0, frame)
            # Progress bar at bottom
            pw = int(bw * progress)
            cv2.rectangle(frame, (x, sy+bh-6), (x+pw, sy+bh), PINK, -1)

        # Label (two lines)
        lines = label.split("\\n")
        line_h = 30
        total_h = len(lines) * line_h
        ty = sy + (bh - total_h) // 2 + line_h - 4
        txt_col = (0,0,0) if (filled and not hovered) else (255,255,255)
        for li, ln in enumerate(lines):
            tw, _ = cv2.getTextSize(ln, cv2.FONT_HERSHEY_DUPLEX, 0.62, 2)[0], None
            tx = x + (bw - tw[0]) // 2 if isinstance(tw, tuple) else x + 20
            sz = cv2.getTextSize(ln, cv2.FONT_HERSHEY_DUPLEX, 0.62, 2)
            tx = x + (bw - sz[0][0]) // 2
            cv2.putText(frame, ln, (tx, ty + li * line_h),
                        cv2.FONT_HERSHEY_DUPLEX, 0.62, txt_col, 2, cv2.LINE_AA)

        button_list.append([mid, x, sy, bw, bh, col, label])

    return button_list


def draw_top_nav(frame, hover_key, progress, mode):
    """Persistent back button + optional SPEAK button."""
    import cv2
    button_list = []
    PINK = (180, 80, 180)

    # Back button
    x, y, w, h = 20, 20, 220, 54
    hovered = hover_key and hover_key[0] == "MAIN_MENU"
    bg = PINK if hovered else (30, 30, 30)
    ov = frame.copy()
    cv2.rectangle(ov, (x,y), (x+w,y+h), bg, -1)
    cv2.addWeighted(ov, 1.0, frame, 0.0, 0, frame)
    cv2.rectangle(frame, (x,y), (x+w,y+h), PINK, 2)
    cv2.putText(frame, "< MAIN MENU", (x+14, y+35),
                cv2.FONT_HERSHEY_DUPLEX, 0.65, (255,255,255), 2, cv2.LINE_AA)
    if hovered:
        pw = int(w * progress)
        cv2.rectangle(frame, (x, y+h-5), (x+pw, y+h), (255,255,255), -1)
    button_list.append(["MAIN_MENU", x, y, w, h, PINK, "BACK"])

    # ASL speak button
    if mode == "ASL":
        sx, sy2, sw, sh = 1050, 20, 200, 54
        shov = hover_key and hover_key[0] == "SPEAK"
        sbg = (40,140,40) if shov else (20,80,20)
        ov2 = frame.copy()
        cv2.rectangle(ov2, (sx,sy2), (sx+sw,sy2+sh), sbg, -1)
        cv2.addWeighted(ov2, 1.0, frame, 0.0, 0, frame)
        cv2.rectangle(frame, (sx,sy2), (sx+sw,sy2+sh), (40,200,40), 2)
        cv2.putText(frame, "SPEAK", (sx+50, sy2+36),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (255,255,255), 2, cv2.LINE_AA)
        if shov:
            pw = int(sw * progress)
            cv2.rectangle(frame, (sx, sy2+sh-5), (sx+pw, sy2+sh), (255,255,255), -1)
        button_list.append(["SPEAK", sx, sy2, sw, sh, (40,200,40), "SPEAK"])

    return button_list


def check_escape_gesture(results, frame_w, frame_h):
    """Return True if both hands are open palms (escape gesture)."""
    if not results.multi_hand_landmarks or len(results.multi_hand_landmarks) < 2:
        return False
    open_hands = 0
    for handLms in results.multi_hand_landmarks:
        lm = [(int(l.x*frame_w), int(l.y*frame_h)) for l in handLms.landmark]
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        up = sum(1 for t, p in zip(tips, pips) if lm[t][1] < lm[p][1])
        if up >= 3:
            open_hands += 1
    return open_hands >= 2

'''

# Insert before the keyboard renderer
idx = code.find(MARKER)
if idx == -1:
    print("ERROR: keyboard renderer marker not found")
    sys.exit(1)
code = code[:idx] + INJECT + code[idx:]

# 4. Replace the main loop button-list + hand detection block
OLD_LOOP = '''            button_list      = draw_keyboard(frame, predictions=predictions,
                                             mode=input_mode,
                                             theme_idx=current_theme,
                                             asl_letter=asl_stable,
                                             asl_progress=min((time.time()-asl_t0)/ASL_HOLD_TIME,1.0) if asl_stable else 0.0)
            active_highlight = None
            progress_pct     = 0.0

            if result.multi_hand_landmarks:
                for handLms in result.multi_hand_landmarks:
                    lm = [(int(l.x*w),int(l.y*h)) for l in handLms.landmark]'''

NEW_LOOP = '''            if input_mode == "MAIN_MENU":
                button_list = draw_main_menu(frame, active_highlight, progress_pct)
            else:
                button_list = draw_top_nav(frame, active_highlight, progress_pct, input_mode)
                if input_mode not in ("ASSIST", "MEMO", "AIR"):
                    button_list += draw_keyboard(frame, predictions=predictions,
                                                 mode=input_mode,
                                                 theme_idx=current_theme,
                                                 asl_letter=asl_stable,
                                                 asl_progress=min((time.time()-asl_t0)/ASL_HOLD_TIME,1.0) if asl_stable else 0.0)

            active_highlight = None
            progress_pct     = 0.0

            if result.multi_hand_landmarks:
                if check_escape_gesture(result, w, h):
                    if escape_start == 0.0:
                        escape_start = time.time()
                    elif time.time() - escape_start > 2.0:
                        input_mode = "MAIN_MENU"
                        escape_start = 0.0
                        cv2.putText(frame, "ESCAPING...", (w//2-150, h//2),
                                    cv2.FONT_HERSHEY_DUPLEX, 1.5, (0,0,255), 4)
                else:
                    escape_start = 0.0

                handLms = result.multi_hand_landmarks[0]
                lm = [(int(l.x*w),int(l.y*h)) for l in handLms.landmark]
                if True:
                    pass  # indent guard'''

if OLD_LOOP not in code:
    print("WARNING: OLD_LOOP not found verbatim - searching for partial match")
else:
    code = code.replace(OLD_LOOP, NEW_LOOP)
    print("Loop block replaced OK")

# 5. Add mode-selection handlers inside the kid == TOGGLE_MODE block
OLD_TOGGLE = '                            elif kid=="CLEAR_CANVAS": drawing_canvas=np.zeros_like(frame)'
NEW_TOGGLE = '''                            elif kid=="MAIN_MENU":
                                input_mode = "MAIN_MENU"
                                escape_start = 0.0
                            elif kid in ("GRID", "ASL", "AIR", "ASSIST", "MEMO"):
                                input_mode = kid
                                drawing_canvas = np.zeros_like(frame)
                                asl_stable = ""; trail.clear(); typed_text = ""
                            elif kid=="CLEAR_CANVAS": drawing_canvas=np.zeros_like(frame)'''
if OLD_TOGGLE in code:
    code = code.replace(OLD_TOGGLE, NEW_TOGGLE)
    print("Toggle block replaced OK")
else:
    print("WARNING: toggle block not found")

# 6. Replace end-of-frame redraw section
OLD_REDRAW = '''            if vis_key and (time.time()-vis_time<0.15): active_highlight=vis_key

            if input_mode not in ("ASL","ASSIST"):
                draw_keyboard(frame,highlight_key=active_highlight,
                              progress=progress_pct,predictions=predictions,
                              mode=input_mode,theme_idx=current_theme)

            if input_mode=="AIR":
                frame=cv2.addWeighted(frame,1,drawing_canvas,0.7,0)

            # Text display
            T=THEMES[current_theme]
            ov=frame.copy()
            cv2.rectangle(ov,(55,30),(1050,115),T["bg"],-1)
            cv2.addWeighted(ov,0.75,frame,0.25,0,frame)
            cv2.rectangle(frame,(55,30),(1050,115),T["border"],1,cv2.LINE_AA)
            cv2.putText(frame,typed_text[-32:],(75,82),
                        cv2.FONT_HERSHEY_SIMPLEX,1.2,T["text"],2,cv2.LINE_AA)

            cv2.imshow("Emergency AI Communication Interface", frame)'''

NEW_REDRAW = '''            if vis_key and (time.time()-vis_time<0.15): active_highlight=vis_key

            if input_mode == "MAIN_MENU":
                draw_main_menu(frame, hover_key=active_highlight, progress=progress_pct)
            else:
                draw_top_nav(frame, hover_key=active_highlight, progress=progress_pct, mode=input_mode)
                if input_mode not in ("ASL","ASSIST","MEMO","AIR"):
                    draw_keyboard(frame, highlight_key=active_highlight,
                                  progress=progress_pct, predictions=predictions,
                                  mode=input_mode, theme_idx=current_theme)

            if input_mode == "AIR":
                frame = cv2.addWeighted(frame, 0.3, np.zeros_like(frame), 0.7, 0)
                frame = cv2.addWeighted(frame, 1, drawing_canvas, 1.0, 0)
            elif input_mode in ("ASSIST", "MEMO"):
                ui_overlay = frame.copy()
                frame[:] = (20, 25, 30)
                cv2.addWeighted(ui_overlay, 1.0, frame, 0.0, 0, frame)
            elif input_mode == "GRID":
                fh2, fw2 = frame.shape[:2]
                cv2.rectangle(frame, (0, fh2//2 - 50), (fw2, fh2), (15, 12, 10), -1)

            if input_mode in ("GRID", "AIR", "ASL"):
                T = THEMES[current_theme]
                ov = frame.copy()
                cv2.rectangle(ov, (55,30), (1050,115), T["bg"], -1)
                cv2.addWeighted(ov, 0.75, frame, 0.25, 0, frame)
                cv2.rectangle(frame, (55,30), (1050,115), T["border"], 1, cv2.LINE_AA)
                cv2.putText(frame, typed_text[-32:], (75,82),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, T["text"], 2, cv2.LINE_AA)
                if input_mode == "ASL":
                    cv2.rectangle(frame, (1080,50), (1250,115), (40,120,40), -1)
                    cv2.putText(frame, "SPEAK", (1090,95),
                                cv2.FONT_HERSHEY_DUPLEX, 1.0, (255,255,255), 2, cv2.LINE_AA)
                    if active_highlight and active_highlight[0] == "SPEAK":
                        cv2.rectangle(frame,(1080,105),(1080+int(170*progress_pct),115),(255,255,255),-1)

            cv2.imshow("Emergency AI Communication Interface", frame)'''

if OLD_REDRAW in code:
    code = code.replace(OLD_REDRAW, NEW_REDRAW)
    print("Redraw block replaced OK")
else:
    print("WARNING: redraw block not found")

# Write output
with open('index.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Done - index.py written successfully")
