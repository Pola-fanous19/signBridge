const Kalidokit = require('./node_modules/kalidokit/dist/kalidokit.umd.js');

const pose3D = new Array(33).fill(0).map(() => ({ x: 0.5, y: 0.5, z: 0, v: 1 }));
try {
  const poseRig = Kalidokit.Pose.solve(pose3D, pose3D, {
    runtime: "mediapipe",
    imageSize: { width: 640, height: 480 }
  });
  console.log("Pose success:", Object.keys(poseRig || {}));
} catch (e) {
  console.error("Pose crash:", e);
}

try {
  const hand3D = new Array(21).fill(0).map(() => ({ x: 0.5, y: 0.5, z: 0, v: 1 }));
  const handRig = Kalidokit.Hand.solve(hand3D, "Right");
  console.log("Hand success:", Object.keys(handRig || {}));
} catch (e) {
  console.error("Hand crash:", e);
}
