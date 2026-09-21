import fs from 'fs';
import path from 'path';
import * as THREE from 'three';
import { solveMHRDirect } from '../frontend/src/lib/mhrDirectSolver.js';
import { createBaseMhrBody } from '../frontend/src/lib/syntheticPoses.js';

// Smooth ease-in-out curve
function easeInOutCubic(x) {
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

const TOTAL_FRAMES = 35;
const rawFrames = [];
const solvedFrames = [];

for (let i = 0; i < TOTAL_FRAMES; i++) {
  const p = easeInOutCubic(Math.min(1.0, i / 20)); // Rises over first 20 frames, holds for remaining 15
  const kps = createBaseMhrBody();

  // 1. Resting Right Arm (hangs naturally along torso)
  kps[6]  = [-0.20, -0.40, 1.80]; // Right shoulder
  kps[8]  = [-0.22, -0.15, 1.80]; // Right elbow (below shoulder)
  kps[41] = [-0.24,  0.12, 1.80]; // Right wrist (down at side)

  // 2. Active Left Arm (starts at waist, rises smoothly to chest)
  kps[5]  = [0.20, -0.40, 1.80]; // Left shoulder

  // Elbow stays safely below shoulder (-0.40) throughout entire motion
  const elbowX = 0.22 + p * 0.02;
  const elbowY = -0.15 - p * 0.08; // -0.15 down to -0.23 (shoulder is -0.40, so 17cm lower!)
  const elbowZ = 1.80 + p * 0.04;
  kps[7] = [elbowX, elbowY, elbowZ];

  // Wrist moves from waist (Y=+0.12) up to chest (Y=-0.32) and forward (+Z)
  const wristX = 0.24 - p * 0.14; // 0.24 -> 0.10 (inward to chest)
  const wristY = 0.12 - p * 0.44; // 0.12 -> -0.32 (up to chest level)
  const wristZ = 1.80 + p * 0.18; // moves forward towards camera
  kps[62] = [wristX, wristY, wristZ];

  // 3. Left Hand Fingers (Morphs from relaxed to Thumbs Up / Call Me)
  const wx = wristX, wy = wristY, wz = wristZ;

  // Thumb: extends UP (-Y) and slightly outward (+X)
  kps[45] = [wx + 0.02 * (1-p) + 0.02 * p, wy + 0.03 * (1-p) - 0.02 * p, wz - 0.02 * (1-p) + 0.01 * p];
  kps[44] = [wx + 0.03 * (1-p) + 0.03 * p, wy + 0.05 * (1-p) - 0.05 * p, wz - 0.02 * (1-p) + 0.02 * p];
  kps[43] = [wx + 0.04 * (1-p) + 0.03 * p, wy + 0.07 * (1-p) - 0.08 * p, wz - 0.02 * (1-p) + 0.03 * p];
  kps[42] = [wx + 0.05 * (1-p) + 0.03 * p, wy + 0.09 * (1-p) - 0.11 * p, wz - 0.02 * (1-p) + 0.04 * p]; // Thumb Tip

  // Pinky: extends outward (+X) for "Call Me" gesture
  kps[61] = [wx + 0.03, wy + 0.04 * (1-p) + 0.01 * p, wz + 0.01 * p];
  kps[60] = [wx + 0.04 * (1-p) + 0.05 * p, wy + 0.06 * (1-p) + 0.01 * p, wz + 0.02 * p];
  kps[59] = [wx + 0.05 * (1-p) + 0.07 * p, wy + 0.08 * (1-p) + 0.01 * p, wz + 0.03 * p];
  kps[58] = [wx + 0.06 * (1-p) + 0.09 * p, wy + 0.10 * (1-p) + 0.01 * p, wz + 0.04 * p]; // Pinky Tip

  // Index, Middle, Ring: curl tightly into palm
  const curledFingers = [
    [49, 48, 47, 46], // Index
    [53, 52, 51, 50], // Middle
    [57, 56, 55, 54]  // Ring
  ];

  curledFingers.forEach((indices, fIdx) => {
    const xOff = (fIdx - 1.0) * 0.015;
    // Relaxed (p=0) vs Curled (p=1)
    kps[indices[0]] = [wx + xOff, wy + 0.04 * (1-p) - 0.02 * p, wz + 0.00 * (1-p) - 0.02 * p];
    kps[indices[1]] = [wx + xOff, wy + 0.06 * (1-p) + 0.00 * p, wz + 0.00 * (1-p) - 0.04 * p];
    kps[indices[2]] = [wx + xOff, wy + 0.08 * (1-p) + 0.02 * p, wz + 0.00 * (1-p) - 0.03 * p];
    kps[indices[3]] = [wx + xOff, wy + 0.10 * (1-p) + 0.02 * p, wz + 0.00 * (1-p) - 0.01 * p];
  });

  rawFrames.push(kps);

  // Compute live kinematics with relaxRight = true (idle arm)
  const solved = solveMHRDirect(kps, { relaxRight: true });

  // Convert Quaternions to serializable [x, y, z, w] arrays
  const serializableFrame = {
    isMhrDirect: true,
    pose: {},
    leftHand: {},
    rightHand: {}
  };

  for (const [k, q] of Object.entries(solved.pose)) {
    serializableFrame.pose[k] = [q.x, q.y, q.z, q.w];
  }
  for (const [k, q] of Object.entries(solved.leftHand)) {
    serializableFrame.leftHand[k] = [q.x, q.y, q.z, q.w];
  }
  for (const [k, q] of Object.entries(solved.rightHand)) {
    serializableFrame.rightHand[k] = [q.x, q.y, q.z, q.w];
  }

  solvedFrames.push(serializableFrame);
}

const outData = {
  name: 'TEST',
  fps: 30,
  isHolisticResult: true,
  frames: solvedFrames,
  rawFrames: rawFrames
};

const targetPath = path.resolve('backend/data/lexicon/words/TEST.json');
fs.writeFileSync(targetPath, JSON.stringify(outData, null, 2), 'utf8');

console.log(`[+] Generated fresh dynamic calculation for TEST (${TOTAL_FRAMES} frames)!`);
console.log(`[+] Saved rawFrames (70 keypoints) + solvedFrames (quaternions) to ${targetPath}`);
