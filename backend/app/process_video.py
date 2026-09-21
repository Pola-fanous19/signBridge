import os
import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from .one_euro_filter import OneEuroFilter

# Go up one directory level from 'app' to 'backend'
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')

# Configuration
POSE_MODEL_PATH = os.path.join(MODELS_DIR, 'pose_landmarker_heavy.task')
HAND_MODEL_PATH = os.path.join(MODELS_DIR, 'hand_landmarker.task')
FACE_MODEL_PATH = os.path.join(MODELS_DIR, 'face_landmarker.task')

def init_landmarkers():
    base_options = python.BaseOptions

    # POSE
    pose_options = vision.PoseLandmarkerOptions(
        base_options=base_options(model_asset_path=POSE_MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        output_segmentation_masks=False
    )
    pose_landmarker = vision.PoseLandmarker.create_from_options(pose_options)

    # HANDS
    hand_options = vision.HandLandmarkerOptions(
        base_options=base_options(model_asset_path=HAND_MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )
    hand_landmarker = vision.HandLandmarker.create_from_options(hand_options)

    # FACE
    face_options = vision.FaceLandmarkerOptions(
        base_options=base_options(model_asset_path=FACE_MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1
    )
    face_landmarker = vision.FaceLandmarker.create_from_options(face_options)

    return pose_landmarker, hand_landmarker, face_landmarker

def _serialize_landmarks(landmark_list):
    if not landmark_list:
        return None
    return [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": getattr(lm, 'visibility', getattr(lm, 'presence', 1.0))} for lm in landmark_list]

def process_video_file(video_path):
    """
    Processes a video file through Heavy MediaPipe Tasks and applies 1-Euro Filter to Z-depth.
    Returns a list of frames compatible with Kalidokit's expected input structure.
    """
    pose_landmarker, hand_landmarker, face_landmarker = init_landmarkers()

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 30
    
    frames_data = []
    
    # 1-Euro Filters (We need one for each type of landmark)
    # We will initialize them dynamically on the first frame where the body part is detected
    pose_filter = None
    pose_world_filter = None
    left_hand_filter = None
    right_hand_filter = None
    face_filter = None

    def apply_filter(filter_obj, current_time, landmarks):
        if not landmarks: return None, filter_obj
        
        # Convert to numpy array of shape (N, 3)
        coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
        
        if filter_obj is None:
            filter_obj = OneEuroFilter(t0=current_time, x0=coords)
            filtered_coords = coords
        else:
            filtered_coords = filter_obj(current_time, coords)
            
        # Reconstruct landmark objects (we just mock them using a dict or simple object)
        class MockLandmark:
            def __init__(self, x, y, z, v):
                self.x = x
                self.y = y
                self.z = z
                self.visibility = v
                self.presence = v
                
        return [MockLandmark(fc[0], fc[1], fc[2], orig.visibility if hasattr(orig, 'visibility') else getattr(orig, 'presence', 1.0)) 
                for fc, orig in zip(filtered_coords, landmarks)], filter_obj


    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int((frame_idx / fps) * 1000)
        timestamp_s = timestamp_ms / 1000.0
        
        # We need strictly monotonic increasing timestamps
        if frame_idx > 0 and timestamp_ms <= frames_data[-1].get('_ts_ms', 0):
            timestamp_ms = frames_data[-1].get('_ts_ms', 0) + 1
            timestamp_s = timestamp_ms / 1000.0

        # Run models
        pose_result = pose_landmarker.detect_for_video(mp_image, timestamp_ms)
        hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)
        face_result = face_landmarker.detect_for_video(mp_image, timestamp_ms)
        
        # Extract raw arrays
        raw_pose = pose_result.pose_landmarks[0] if pose_result.pose_landmarks else None
        raw_pose_world = pose_result.pose_world_landmarks[0] if pose_result.pose_world_landmarks else None
        
        raw_left_hand = None
        raw_right_hand = None
        if hand_result.hand_landmarks:
            for idx, handedness in enumerate(hand_result.handedness):
                # MediaPipe tasks handedness output is natively mirrored unless selfie mode is off.
                # Usually: 'Left' means the person's physical Left hand.
                cat_name = handedness[0].category_name
                if cat_name == 'Left':
                    raw_left_hand = hand_result.hand_landmarks[idx]
                elif cat_name == 'Right':
                    raw_right_hand = hand_result.hand_landmarks[idx]
                    
        raw_face = face_result.face_landmarks[0] if face_result.face_landmarks else None

        # Apply 1 Euro Filter
        filtered_pose, pose_filter = apply_filter(pose_filter, timestamp_s, raw_pose)
        filtered_pose_world, pose_world_filter = apply_filter(pose_world_filter, timestamp_s, raw_pose_world)
        filtered_left_hand, left_hand_filter = apply_filter(left_hand_filter, timestamp_s, raw_left_hand)
        filtered_right_hand, right_hand_filter = apply_filter(right_hand_filter, timestamp_s, raw_right_hand)
        filtered_face, face_filter = apply_filter(face_filter, timestamp_s, raw_face)

        # Build JSON frame
        frame_dict = {
            "isHolisticResult": True,
            "_ts_ms": timestamp_ms,
            "poseLandmarks": _serialize_landmarks(filtered_pose),
            "poseWorldLandmarks": _serialize_landmarks(filtered_pose_world),
            "leftHandLandmarks": _serialize_landmarks(filtered_left_hand),
            "rightHandLandmarks": _serialize_landmarks(filtered_right_hand),
            "faceLandmarks": _serialize_landmarks(filtered_face)
        }
        
        frames_data.append(frame_dict)
        frame_idx += 1

    cap.release()
    pose_landmarker.close()
    hand_landmarker.close()
    face_landmarker.close()
    
    return frames_data
