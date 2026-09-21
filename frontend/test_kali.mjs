(async () => {
  const { frameForLetter } = await import('./src/lib/fingerspell.js');
  const k = await import('./node_modules/kalidokit/dist/kalidokit.umd.js');
  
  const L = frameForLetter('W').landmarks;
  const p = L.slice(0, 33);
  const rig = k.default.Pose.solve(p, p, {runtime: 'mediapipe'});
  console.log("Pose Rig:", rig.RightUpperArm);
  
  const h = L.slice(64, 85);
  const hRig = k.default.Hand.solve(h, 'Right');
  console.log("Hand Rig:", hRig.RightWrist);
})();
