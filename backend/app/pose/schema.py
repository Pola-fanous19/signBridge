"""Landmark schema - must match frontend/src/lib/schema.js."""

POSE_LANDMARKS = 33
FACE_KEYPOINTS = 10
HAND_LANDMARKS = 21
TOTAL_LANDMARKS = POSE_LANDMARKS + FACE_KEYPOINTS + HAND_LANDMARKS + HAND_LANDMARKS

POSE_IDX = {
    "NOSE": 0,
    "L_SHOULDER": 11, "R_SHOULDER": 12,
    "L_ELBOW": 13,    "R_ELBOW": 14,
    "L_WRIST": 15,    "R_WRIST": 16,
    "L_HIP": 23,      "R_HIP": 24,
}

LEFT_HAND_START = POSE_LANDMARKS + FACE_KEYPOINTS       # 43
RIGHT_HAND_START = LEFT_HAND_START + HAND_LANDMARKS     # 64


def make_lm(x=0.5, y=0.5, z=0.0, v=1.0):
    return {"x": float(x), "y": float(y), "z": float(z), "v": float(v)}


def neutral_landmarks():
    lm = [make_lm() for _ in range(TOTAL_LANDMARKS)]

    lm[POSE_IDX["NOSE"]]       = make_lm(0.500, 0.190)
    lm[POSE_IDX["L_SHOULDER"]] = make_lm(0.415, 0.320)
    lm[POSE_IDX["R_SHOULDER"]] = make_lm(0.585, 0.320)
    lm[POSE_IDX["L_ELBOW"]]    = make_lm(0.400, 0.480)
    lm[POSE_IDX["R_ELBOW"]]    = make_lm(0.600, 0.480)
    lm[POSE_IDX["L_WRIST"]]    = make_lm(0.395, 0.640)
    lm[POSE_IDX["R_WRIST"]]    = make_lm(0.605, 0.640)
    lm[POSE_IDX["L_HIP"]]      = make_lm(0.445, 0.610)
    lm[POSE_IDX["R_HIP"]]      = make_lm(0.555, 0.610)

    rest = [
        (0.000, 0.000,  0.000),
        (0.030, 0.010,  0.005), (0.055, 0.030,  0.010),
        (0.070, 0.055,  0.010), (0.082, 0.078,  0.010),
        (0.030, 0.055,  0.000), (0.032, 0.100,  0.000),
        (0.033, 0.135, -0.005), (0.034, 0.160, -0.010),
        (0.010, 0.060,  0.000), (0.011, 0.110,  0.000),
        (0.012, 0.150, -0.005), (0.012, 0.178, -0.010),
        (-0.012, 0.058, 0.000), (-0.014, 0.105, 0.000),
        (-0.015, 0.140,-0.005), (-0.016, 0.164,-0.010),
        (-0.032, 0.052, 0.000), (-0.036, 0.090, 0.000),
        (-0.038, 0.118,-0.005), (-0.040, 0.140,-0.010),
    ]

    for start, wrist_idx, mirror in [
        (LEFT_HAND_START,  POSE_IDX["L_WRIST"], -1),
        (RIGHT_HAND_START, POSE_IDX["R_WRIST"], +1),
    ]:
        w = lm[wrist_idx]
        for i, (dx, dy, dz) in enumerate(rest):
            lm[start + i] = make_lm(
                w["x"] + dx * mirror,
                w["y"] + dy,
                w["z"] + dz,
            )
    return lm


def neutral_frame():
    return {"landmarks": neutral_landmarks(), "non_manual": None}
