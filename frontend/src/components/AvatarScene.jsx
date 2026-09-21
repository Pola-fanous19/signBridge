import React, { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import * as Kalidokit from 'kalidokit/dist/kalidokit.umd.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

import { LEFT_HAND_START, RIGHT_HAND_START } from '../lib/schema.js';

// Lerp factor for smoothing out the mediapipe jitter
const DAMP = 0.4;

import Skeleton3D from './Skeleton3D.jsx';

function VRMAvatar({ frameRef, position = [0, -1.5, 0] }) {
  const [vrm, setVrm] = useState(null);

  const gltf = useLoader(GLTFLoader, "/avatar.vrm", (loader) => {
    loader.register((parser) => new VRMLoaderPlugin(parser));
  });

  useEffect(() => {
    if (gltf && gltf.userData.vrm) {
      const loadedVrm = gltf.userData.vrm;
      // Do not rotate the scene! Kalidokit's Hips rotation handles facing the camera.
      
      // Remove unnecessary joints to prevent VRM bugs
      VRMUtils.combineSkeletons(gltf.scene);
      setVrm(loadedVrm);
    }
  }, [gltf]);

  useFrame((state, delta) => {
    if (!vrm) return;

    const frame = frameRef.current;
    if (frame) {
      // Handle Vite UMD import wrapping
      const PoseSolver = Kalidokit.Pose || Kalidokit.default?.Pose;
      const HandSolver = Kalidokit.Hand || Kalidokit.default?.Hand;
      const FaceSolver = Kalidokit.Face || Kalidokit.default?.Face;

      let poseRig, rightHandRig, leftHandRig, faceRig;

      if (frame.isMhrDirect) {
        // Direct Quaternion Solver Path
        poseRig = { ...(frame.pose || {}) };
        rightHandRig = frame.rightHand;
        leftHandRig = frame.leftHand;
        // All animation paths use the Hips bone, rather than a mix of root
        // and Hips rotations. Existing direct clips already contain this
        // quaternion; newly solved clips receive the same convention here.
        if (!poseRig.Hips) {
          poseRig.Hips = new THREE.Quaternion().setFromAxisAngle(
            new THREE.Vector3(0, 1, 0), Math.PI,
          );
        }
        
      } else if (frame.isHolisticResult) {
        // 1. Live Webcam Mimicry
        const results = frame;
        if (results.poseLandmarks) {
          let pose3D = results.poseWorldLandmarks;
          if (!pose3D) {
            const keys = Object.keys(results);
            for (const key of keys) {
              if (key !== "poseLandmarks" && Array.isArray(results[key]) && results[key].length === 33) {
                pose3D = results[key];
                break;
              }
            }
          }
          
          if (pose3D) {
            const correctedPose3D = pose3D.map(lm => ({ 
              x: -lm.x, 
              y: lm.y, 
              z: lm.z, 
              visibility: (lm.visibility === null || lm.visibility === undefined) ? 1.0 : lm.visibility 
            }));
            
            const correctedPose2D = results.poseLandmarks.map(lm => ({
              x: lm.x,
              y: lm.y,
              z: lm.z,
              visibility: (lm.visibility === null || lm.visibility === undefined) ? 1.0 : lm.visibility
            }));
            
            poseRig = PoseSolver.solve(correctedPose3D, correctedPose2D, {
              runtime: "mediapipe",
              imageSize: { width: 640, height: 480 }
            });
          }
        }
        
        // SWAP HANDS to match the mirrored arms!
        if (results.leftHandLandmarks) {
          rightHandRig = HandSolver.solve(results.leftHandLandmarks, "Right");
        }
        if (results.rightHandLandmarks) {
          leftHandRig = HandSolver.solve(results.rightHandLandmarks, "Left");
        }
        
        if (results.faceLandmarks) {
          faceRig = FaceSolver.solve(results.faceLandmarks, {
            runtime: "mediapipe",
            imageSize: { width: 640, height: 480 }
          });
        }
      } else if (frame.landmarks) {
        // 2. Legacy BOOK.json flat array fallback
        const L = frame.landmarks;
        const pose3D = L.slice(0, 33);
        poseRig = PoseSolver.solve(pose3D, pose3D, {
          runtime: "mediapipe",
          imageSize: { width: 640, height: 480 }
        });
        const rightHandLMs = L.slice(RIGHT_HAND_START, RIGHT_HAND_START + 21);
        rightHandRig = HandSolver.solve(rightHandLMs, "Right");
        const leftHandLMs = L.slice(LEFT_HAND_START, LEFT_HAND_START + 21);
        leftHandRig = HandSolver.solve(leftHandLMs, "Left");
      }

      const applyRig = (rig) => {
        if (!rig) return;
        Object.keys(rig).forEach(vrmName => {
          let camelCaseName = vrmName.charAt(0).toLowerCase() + vrmName.slice(1);
          
          // Map Kalidokit Wrist to VRM Hand
          if (camelCaseName === 'rightWrist') camelCaseName = 'rightHand';
          if (camelCaseName === 'leftWrist') camelCaseName = 'leftHand';

          let boneNode = vrm.humanoid.getNormalizedBoneNode(camelCaseName);
          
          // VRM 1.0 Thumb compatibility fallback
          if (!boneNode) {
            if (camelCaseName === 'rightThumbProximal') boneNode = vrm.humanoid.getNormalizedBoneNode('rightThumbMetacarpal');
            else if (camelCaseName === 'rightThumbIntermediate') boneNode = vrm.humanoid.getNormalizedBoneNode('rightThumbProximal');
            else if (camelCaseName === 'leftThumbProximal') boneNode = vrm.humanoid.getNormalizedBoneNode('leftThumbMetacarpal');
            else if (camelCaseName === 'leftThumbIntermediate') boneNode = vrm.humanoid.getNormalizedBoneNode('leftThumbProximal');
          }
          
          if (boneNode) {
            let rot = rig[vrmName];
            if (vrmName === "Hips" && rot && rot.rotation) {
              rot = rot.rotation;
            }
            if (!rot) return;

            let targetQuat;
            if (rot && (rot.isQuaternion || rot instanceof THREE.Quaternion)) {
              targetQuat = rot;
            } else if (Array.isArray(rot) && rot.length === 4) {
              // Rehydrated [x, y, z, w] Quaternion from JSON database
              targetQuat = new THREE.Quaternion(rot[0], rot[1], rot[2], rot[3]);
            } else if (rot && (rot.w !== undefined || rot._w !== undefined)) {
              // Rehydrated {x, y, z, w} object
              const x = rot.x !== undefined ? rot.x : rot._x;
              const y = rot.y !== undefined ? rot.y : rot._y;
              const z = rot.z !== undefined ? rot.z : rot._z;
              const w = rot.w !== undefined ? rot.w : rot._w;
              targetQuat = new THREE.Quaternion(x, y, z, w);
            } else if (rot && !isNaN(rot.x) && !isNaN(rot.y) && !isNaN(rot.z)) {
              if (vrmName === "Spine") rot.y = 0;
              targetQuat = new THREE.Quaternion().setFromEuler(
                new THREE.Euler(rot.x, rot.y, rot.z, 'XYZ')
              );
            } else {
              return;
            }
            
            boneNode.quaternion.slerp(targetQuat, DAMP);
            
            // If it's Spine, distribute a fraction to Chest and UpperChest
            if (vrmName === "Spine" && !(rot instanceof THREE.Quaternion) && !Array.isArray(rot)) {
              const chestNode = vrm.humanoid.getNormalizedBoneNode('chest');
              const upperChestNode = vrm.humanoid.getNormalizedBoneNode('upperChest');
              if (chestNode) chestNode.quaternion.slerp(targetQuat, DAMP);
              if (upperChestNode) upperChestNode.quaternion.slerp(targetQuat, DAMP);
            }
          }
        });
      };

      if (poseRig) {
        applyRig({
          Spine: poseRig.Spine,
          Hips: poseRig.Hips,
          Neck: poseRig.Neck,
          Head: poseRig.Head,
          RightUpperArm: poseRig.RightUpperArm,
          RightLowerArm: poseRig.RightLowerArm,
          RightHand: poseRig.RightHand,
          LeftUpperArm: poseRig.LeftUpperArm,
          LeftLowerArm: poseRig.LeftLowerArm,
          LeftHand: poseRig.LeftHand
        });
      }

      if (rightHandRig) applyRig(rightHandRig);
      if (leftHandRig) applyRig(leftHandRig);

      // --- FACIAL EXPRESSIONS & HEAD ---
      if (faceRig) {
        if (faceRig.head) {
          const headNode = vrm.humanoid.getNormalizedBoneNode('head');
          const neckNode = vrm.humanoid.getNormalizedBoneNode('neck');
          const h = faceRig.head;
          const halfQuat = new THREE.Quaternion().setFromEuler(new THREE.Euler(h.x/2, h.y/2, h.z/2, 'XYZ'));
          if (headNode) headNode.quaternion.slerp(halfQuat, DAMP);
          if (neckNode) neckNode.quaternion.slerp(halfQuat, DAMP);
        }
        
        if (vrm.expressionManager) {
          const shape = faceRig.mouth.shape;
          vrm.expressionManager.setValue('blinkLeft', 1 - faceRig.eye.l);
          vrm.expressionManager.setValue('blinkRight', 1 - faceRig.eye.r);
          vrm.expressionManager.setValue('aa', shape.A);
          vrm.expressionManager.setValue('ee', shape.E);
          vrm.expressionManager.setValue('ih', shape.I);
          vrm.expressionManager.setValue('oh', shape.O);
          vrm.expressionManager.setValue('ou', shape.U);
          
          const mouthWidth = faceRig.mouth.x;
          const browHeight = faceRig.brow;
          vrm.expressionManager.setValue('happy', mouthWidth > 0.4 ? (mouthWidth - 0.4) * 2 : 0);
          vrm.expressionManager.setValue('surprised', browHeight > 0.1 ? browHeight * 2 : 0);
          vrm.expressionManager.setValue('angry', browHeight < -0.05 ? Math.abs(browHeight) * 2 : 0);
          vrm.expressionManager.setValue('sad', browHeight < -0.1 && mouthWidth < 0.2 ? 0.5 : 0);
          
          const lookAt = vrm.lookAt;
          if (lookAt && faceRig.pupil) {
            lookAt.applier.applyYawPitch(faceRig.pupil.x, faceRig.pupil.y);
          }
        }
      }
    }

    // Update VRM logic (spring bones, physics, expressions)
    vrm.update(delta);
  });

  return vrm ? <primitive object={vrm.scene} position={position} scale={1.3} /> : null;
}

export default function AvatarScene({
  frameRef,
  rawPoints,
  debugSettings = {}
}) {
  const {
    showSkeleton = false,
    sideBySide = false,
    flipX = false,
    flipY = true,
    flipZ = true
  } = debugSettings;

  const skeletonPos = sideBySide ? [-0.8, -0.2, 0] : [0, -0.2, 0];
  const avatarPos = sideBySide ? [0.6, -1.5, 0] : [0, -1.5, 0];

  return (
    <Canvas
      camera={{ position: [0, 0.2, sideBySide ? 3.2 : 2.5], fov: 45 }}
      dpr={[1, 2]}
      shadows={false}
      gl={{ antialias: true, alpha: false }}
      style={{ width: '100%', height: '100%', background: '#06101f' }}
    >
      <color attach="background" args={['#06101f']} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[2, 3, 4]} intensity={1.2} />
      <directionalLight position={[-3, 1, -2]} intensity={0.5} color="#88aaff" />
      <hemisphereLight args={[0xd0e6ff, 0x1a2540, 0.5]} />

      {/* Sleek stage floor */}
      <mesh position={[0, -1.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[2.5, 48]} />
        <meshStandardMaterial color="#0a1428" roughness={0.9} />
      </mesh>

      <React.Suspense fallback={null}>
        <VRMAvatar frameRef={frameRef} position={avatarPos} />
      </React.Suspense>

      {showSkeleton && rawPoints && (
        <Skeleton3D
          points={rawPoints}
          position={skeletonPos}
          scale={1.3}
          flipX={flipX}
          flipY={flipY}
          flipZ={flipZ}
        />
      )}

      <OrbitControls
        enablePan={true}
        minDistance={1.2}
        maxDistance={5}
        target={[0, 0, 0]}
      />
    </Canvas>
  );
}
