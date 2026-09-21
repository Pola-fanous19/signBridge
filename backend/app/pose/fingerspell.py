"""Server-side ASL fingerspelling.

Mirrors frontend/src/lib/fingerspell.js so REST clients get anatomically
correct 21-landmark handshapes.
"""

from app.pose.schema import (
    HAND_LANDMARKS, POSE_IDX, RIGHT_HAND_START,
    neutral_landmarks, make_lm,
)

FINGER_COLUMNS = {
    "index":  (0.033,  0.058, 0.105),
    "middle": (0.011,  0.062, 0.117),
    "ring":   (-0.013, 0.060, 0.108),
    "pinky":  (-0.034, 0.054, 0.088),
}


def _build_finger(name, state):
    mcpX, mcpY, L = FINGER_COLUMNS[name]
    mcp = (mcpX, mcpY, 0.0)
    if state == "ext":
        return [mcp,
                (mcpX,        mcpY + L * 0.32, 0.005),
                (mcpX,        mcpY + L * 0.65, 0.010),
                (mcpX,        mcpY + L * 0.98, 0.012)]
    if state == "curl":
        return [mcp,
                (mcpX,        mcpY + L * 0.30,  0.030),
                (mcpX * 0.85, mcpY + L * 0.22,  0.055),
                (mcpX * 0.70, mcpY + L * 0.08,  0.045)]
    if state == "halfCurl":
        return [mcp,
                (mcpX, mcpY + L * 0.30, 0.020),
                (mcpX, mcpY + L * 0.35, 0.055),
                (mcpX, mcpY + L * 0.30, 0.080)]
    if state == "hook":
        return [mcp,
                (mcpX, mcpY + L * 0.35, 0.015),
                (mcpX, mcpY + L * 0.42, 0.055),
                (mcpX, mcpY + L * 0.30, 0.070)]
    return _build_finger(name, "ext")


def _build_thumb(state):
    if state == "across":
        return [(0.028, 0.020, 0.015), (0.030, 0.048, 0.020),
                (0.020, 0.070, 0.025), (0.008, 0.078, 0.028)]
    if state == "sideOut":
        return [(0.035, 0.010, 0.010), (0.075, 0.008, 0.010),
                (0.108, 0.010, 0.010), (0.135, 0.015, 0.010)]
    if state == "up":
        return [(0.038, 0.020, 0.015), (0.048, 0.055, 0.015),
                (0.052, 0.090, 0.015), (0.055, 0.118, 0.015)]
    if state == "tuck":
        return [(0.028, 0.018, 0.020), (0.020, 0.045, 0.045),
                (0.008, 0.055, 0.060), (-0.004, 0.058, 0.062)]
    if state == "touchIndex":
        return [(0.032, 0.020, 0.015), (0.045, 0.048, 0.030),
                (0.048, 0.075, 0.040), (0.040, 0.095, 0.048)]
    if state == "touchMiddle":
        return [(0.030, 0.020, 0.015), (0.038, 0.048, 0.030),
                (0.032, 0.075, 0.045), (0.020, 0.092, 0.050)]
    return [(0.032, 0.015, 0.012), (0.055, 0.035, 0.014),
            (0.070, 0.058, 0.014), (0.082, 0.080, 0.014)]


def _make_hand(spec):
    pts = [None] * 21
    pts[0] = (0.0, 0.0, 0.0)
    t = _build_thumb(spec["thumb"])
    pts[1], pts[2], pts[3], pts[4] = t
    idx = _build_finger("index",  spec["index"])
    mid = _build_finger("middle", spec["middle"])
    rng = _build_finger("ring",   spec["ring"])
    pky = _build_finger("pinky",  spec["pinky"])
    for base, arr in ((5, idx), (9, mid), (13, rng), (17, pky)):
        for i in range(4):
            pts[base + i] = arr[i]
    return pts


LETTER_SHAPES = {
    "A": dict(thumb="across",      index="curl", middle="curl", ring="curl", pinky="curl"),
    "B": dict(thumb="across",      index="ext",  middle="ext",  ring="ext",  pinky="ext"),
    "C": dict(thumb="up",          index="halfCurl", middle="halfCurl", ring="halfCurl", pinky="halfCurl"),
    "D": dict(thumb="touchMiddle", index="ext",  middle="curl", ring="curl", pinky="curl"),
    "E": dict(thumb="tuck",        index="halfCurl", middle="halfCurl", ring="halfCurl", pinky="halfCurl"),
    "F": dict(thumb="touchIndex",  index="curl", middle="ext",  ring="ext",  pinky="ext"),
    "G": dict(thumb="sideOut",     index="ext",  middle="curl", ring="curl", pinky="curl"),
    "H": dict(thumb="across",      index="ext",  middle="ext",  ring="curl", pinky="curl"),
    "I": dict(thumb="across",      index="curl", middle="curl", ring="curl", pinky="ext"),
    "J": dict(thumb="across",      index="curl", middle="curl", ring="curl", pinky="ext"),
    "K": dict(thumb="up",          index="ext",  middle="ext",  ring="curl", pinky="curl"),
    "L": dict(thumb="sideOut",     index="ext",  middle="curl", ring="curl", pinky="curl"),
    "M": dict(thumb="across",      index="curl", middle="curl", ring="curl", pinky="curl"),
    "N": dict(thumb="across",      index="curl", middle="curl", ring="curl", pinky="curl"),
    "O": dict(thumb="touchIndex",  index="curl", middle="curl", ring="curl", pinky="curl"),
    "P": dict(thumb="up",          index="ext",  middle="ext",  ring="curl", pinky="curl"),
    "Q": dict(thumb="sideOut",     index="ext",  middle="curl", ring="curl", pinky="curl"),
    "R": dict(thumb="across",      index="ext",  middle="ext",  ring="curl", pinky="curl"),
    "S": dict(thumb="across",      index="curl", middle="curl", ring="curl", pinky="curl"),
    "T": dict(thumb="across",      index="curl", middle="curl", ring="curl", pinky="curl"),
    "U": dict(thumb="across",      index="ext",  middle="ext",  ring="curl", pinky="curl"),
    "V": dict(thumb="across",      index="ext",  middle="ext",  ring="curl", pinky="curl"),
    "W": dict(thumb="across",      index="ext",  middle="ext",  ring="ext",  pinky="curl"),
    "X": dict(thumb="across",      index="hook", middle="curl", ring="curl", pinky="curl"),
    "Y": dict(thumb="sideOut",     index="curl", middle="curl", ring="curl", pinky="ext"),
    "Z": dict(thumb="across",      index="ext",  middle="curl", ring="curl", pinky="curl"),
}


def _apply_tweaks(letter, hand):
    p = [list(pt) for pt in hand]

    def setp(i, x=None, y=None, z=None):
        if x is not None: p[i][0] = x
        if y is not None: p[i][1] = y
        if z is not None: p[i][2] = z

    if letter == "V":
        for i, dx in ((6, 0.010), (7, 0.020), (8, 0.030)):
            p[i][0] += dx
        for i, dx in ((10, -0.010), (11, -0.020), (12, -0.030)):
            p[i][0] += dx
    elif letter == "R":
        for i, dx in ((6, -0.015), (7, -0.020), (8, -0.024)):
            p[i][0] += dx
        for i, dx in ((10, 0.006), (11, 0.006), (12, 0.006)):
            p[i][0] += dx
        p[8][2] += 0.010
    elif letter == "U":
        for i, dx in ((6, -0.006), (7, -0.006), (8, -0.006)):
            p[i][0] += dx
        for i, dx in ((10, 0.006), (11, 0.006), (12, 0.006)):
            p[i][0] += dx
    elif letter == "W":
        p[8][0]  += 0.014
        p[16][0] -= 0.014
    elif letter == "T":
        setp(3, x=0.020, y=0.060, z=0.028)
        setp(4, x=0.020, y=0.078, z=0.030)
    elif letter == "M":
        setp(4, x=-0.020, y=0.055, z=0.030)
    elif letter == "N":
        setp(4, x=-0.005, y=0.055, z=0.030)
    elif letter == "S":
        setp(1, x=0.030, y=0.040, z=0.030)
        setp(2, x=0.010, y=0.055, z=0.040)
        setp(3, x=-0.010, y=0.060, z=0.045)
        setp(4, x=-0.028, y=0.058, z=0.045)
    elif letter == "O":
        setp(8,  x=0.036, y=0.098, z=0.048)
        setp(12, x=0.025, y=0.100, z=0.052)
        setp(16, x=0.010, y=0.095, z=0.050)
        setp(20, x=-0.005, y=0.088, z=0.045)
    elif letter == "C":
        for tip in (8, 12, 16, 20):
            p[tip][1] -= 0.005
            p[tip][2] += 0.020
    elif letter == "G":
        setp(6, x=0.070, y=0.058, z=0.005)
        setp(7, x=0.105, y=0.058, z=0.005)
        setp(8, x=0.135, y=0.058, z=0.005)
    elif letter in ("K", "P"):
        setp(10, y=0.100, z=0.020)
        setp(11, y=0.098, z=0.055)
        setp(12, y=0.075, z=0.075)
    return p


def frame_for_letter(letter):
    up = (letter or "").upper()
    lm = neutral_landmarks()
    if up not in LETTER_SHAPES:
        return {"landmarks": lm, "non_manual": None}

    hand_local = _apply_tweaks(up, _make_hand(LETTER_SHAPES[up]))

    wrist = lm[POSE_IDX["R_WRIST"]]
    HAND_LIFT_Y = -0.20
    HAND_OFFSET_X = 0.02

    for i in range(HAND_LANDMARKS):
        px, py, pz = hand_local[i]
        lm[RIGHT_HAND_START + i] = make_lm(
            wrist["x"] + px + HAND_OFFSET_X,
            wrist["y"] - py + HAND_LIFT_Y,
            wrist["z"] + pz,
        )
    lm[POSE_IDX["R_WRIST"]] = make_lm(
        wrist["x"] + HAND_OFFSET_X,
        wrist["y"] + HAND_LIFT_Y,
        wrist["z"],
    )
    lm[POSE_IDX["R_ELBOW"]] = make_lm(0.62, 0.42)
    return {"landmarks": lm, "non_manual": None}


def fingerspell_clip(text, fps=30, hold=10, gap=4):
    letters = [c for c in text.upper() if c.isalpha()]
    frames = []
    per_letter = []
    cursor = 0
    for L in letters:
        key = frame_for_letter(L)
        start = cursor
        for _ in range(hold):
            frames.append({"landmarks": list(key["landmarks"]),
                           "non_manual": None})
        cursor += hold
        for _ in range(gap):
            frames.append({"landmarks": list(key["landmarks"]),
                           "non_manual": None})
        cursor += gap
        per_letter.append({"letter": L, "start": start, "end": cursor - 1})
    if not frames:
        from .schema import neutral_frame
        frames.append(neutral_frame())
    return {"frames": frames, "fps": fps}, per_letter
