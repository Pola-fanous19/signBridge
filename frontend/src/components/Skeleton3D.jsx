import React, { useMemo } from 'react';
import * as THREE from 'three';

// MHR-70 Topological bone connections
export const MHR_BONES = [
  // Torso & Head
  [0, 69], // nose -> neck
  [69, 5], [69, 6], // neck -> shoulders
  [5, 6],  // left shoulder -> right shoulder
  [5, 9], [6, 10],  // shoulders -> hips
  [9, 10], // left hip -> right hip
  [9, 11], [11, 13], // left leg
  [10, 12], [12, 14], // right leg

  // Left Arm (Viewer's right side)
  [5, 7],   // shoulder -> elbow
  [7, 62],  // elbow -> wrist

  // Right Arm (Viewer's left side)
  [6, 8],   // shoulder -> elbow
  [8, 41],  // elbow -> wrist

  // Left Hand Fingers
  [62, 45], [45, 44], [44, 43], [43, 42], // Thumb
  [62, 49], [49, 48], [48, 47], [47, 46], // Index
  [62, 53], [53, 52], [52, 51], [51, 50], // Middle
  [62, 57], [57, 56], [56, 55], [55, 54], // Ring
  [62, 61], [61, 60], [60, 59], [59, 58], // Pinky

  // Right Hand Fingers
  [41, 24], [24, 23], [23, 22], [22, 21], // Thumb
  [41, 28], [28, 27], [27, 26], [26, 25], // Index
  [41, 32], [32, 31], [31, 30], [30, 29], // Middle
  [41, 36], [36, 35], [35, 34], [34, 33], // Ring
  [41, 40], [40, 39], [39, 38], [38, 37]  // Pinky
];

// MediaPipe 33-point Holistic Pose bones
export const MEDIAPIPE_POSE_BONES = [
  [0, 1], [1, 2], [2, 3], [3, 7],
  [0, 4], [4, 5], [5, 6], [6, 8],
  [9, 10],
  [11, 12], [11, 13], [13, 15],
  [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28]
];

export default function Skeleton3D({
  points,
  bones = MHR_BONES,
  position = [-1.3, 0, 0],
  scale = 1.0,
  flipX = false,
  flipY = true,  // MHR +Y is down, so default true aligns with Three.js +Y up
  flipZ = true,
  color = '#00ff88',
  visible = true
}) {
  if (!visible || !points || !points.length) return null;

  // Convert raw points array to Three.js Vector3 array
  const vectors = useMemo(() => {
    return points.map(p => {
      if (!p) return new THREE.Vector3(0, 0, 0);
      let x = Array.isArray(p) ? p[0] : p.x ?? 0;
      let y = Array.isArray(p) ? p[1] : p.y ?? 0;
      let z = Array.isArray(p) ? p[2] : p.z ?? 0;

      if (flipX) x = -x;
      if (flipY) y = -y;
      if (flipZ) z = -z;

      return new THREE.Vector3(x * scale, y * scale, z * scale);
    });
  }, [points, scale, flipX, flipY, flipZ]);

  // Build line segments geometry
  const lineGeometry = useMemo(() => {
    const linePositions = [];
    bones.forEach(([i, j]) => {
      const vA = vectors[i];
      const vB = vectors[j];
      if (vA && vB && (vA.lengthSq() > 0 || vB.lengthSq() > 0)) {
        linePositions.push(vA.x, vA.y, vA.z);
        linePositions.push(vB.x, vB.y, vB.z);
      }
    });
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
    return geom;
  }, [vectors, bones]);

  return (
    <group position={position}>
      {/* 1. Bone connecting lines */}
      <lineSegments geometry={lineGeometry}>
        <lineBasicMaterial color={color} linewidth={2} />
      </lineSegments>

      {/* 2. Keypoint spheres */}
      {vectors.map((v, i) => {
        if (v.lengthSq() === 0) return null;
        // Differentiate hands with distinct colors:
        // Left hand (42..62): Cyan
        // Right hand (21..41): Orange
        // Head / Nose (0..4): Gold
        let ptColor = color;
        if (i >= 42 && i <= 62) ptColor = '#00e5ff';
        else if (i >= 21 && i <= 41) ptColor = '#ff9100';
        else if (i <= 4) ptColor = '#ffd600';

        const isJoint = i === 5 || i === 6 || i === 7 || i === 8 || i === 41 || i === 62;
        const radius = isJoint ? 0.025 : 0.012;

        return (
          <mesh key={i} position={[v.x, v.y, v.z]}>
            <sphereGeometry args={[radius, 8, 8]} />
            <meshBasicMaterial color={ptColor} />
          </mesh>
        );
      })}
    </group>
  );
}
