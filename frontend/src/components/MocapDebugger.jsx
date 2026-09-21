import React, { useState, useEffect, useRef, useCallback } from 'react';
import { solveMHRDirect, solveMHRSequence, REST_ARM_LEFT, REST_ARM_RIGHT } from '../lib/mhrDirectSolver.js';
import { SYNTHETIC_PRESETS } from '../lib/syntheticPoses.js';

export default function MocapDebugger({
  onFrameUpdate,
  onRawPointsUpdate,
  debugSettings,
  onSettingsChange
}) {
  const [lexiconWords, setLexiconWords] = useState(['TEST']);
  const [selectedWord, setSelectedWord] = useState('TEST');
  const [sourceType, setSourceType] = useState('lexicon'); // 'lexicon' | 'synthetic' | 'file'
  const [selectedPreset, setSelectedPreset] = useState('t_pose');

  const [framesData, setFramesData] = useState([]);
  const [rawKeypointsData, setRawKeypointsData] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLooping, setIsLooping] = useState(true);
  const [speed, setSpeed] = useState(1.0);
  const [status, setStatus] = useState('');
  // Saved MHR clips are solved as a sequence on load. Re-solving individual
  // frames is useful for experimentation, but intentionally starts disabled
  // because it removes the temporal continuity filter.
  const [liveSolve, setLiveSolve] = useState(false);

  const rafRef = useRef(null);
  const lastTimeRef = useRef(0);
  const animTimeRef = useRef(0);
  const currentIdxRef = useRef(0);

  // 1. Fetch available lexicon words on mount
  useEffect(() => {
    fetch(`/api/lexicon?t=${Date.now()}`)
      .then(res => res.json())
      .then(data => {
        if (data.words && data.words.length) {
          setLexiconWords(data.words);
        }
      })
      .catch(() => {
        // Fallback default list
        setLexiconWords(['TEST', 'BOOK', 'EAT', 'CAT']);
      });
  }, []);

  // 2. Load Lexicon Sign Frames
  const loadLexiconWord = useCallback(async (word) => {
    setStatus(`Loading '${word}'...`);
    try {
      const res = await fetch(`/api/lexicon/${word}?t=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const frames = data.frames || [];
      if (!frames.length) {
        setStatus(`Sign '${word}' has no frames.`);
        return;
      }

      if (Array.isArray(data.rawFrames) && data.rawFrames.length) {
        setRawKeypointsData(data.rawFrames);
        onRawPointsUpdate(data.rawFrames[0]);
        // Live calculate fresh kinematics directly from raw keypoints
        const fresh = solveMHRSequence(data.rawFrames, {
          relaxRight: debugSettings.relaxRight,
          relaxLeft: debugSettings.relaxLeft
        });
        setFramesData(fresh);
        onFrameUpdate(fresh[0]);
        setStatus(`Loaded & calculated '${word}' live (${fresh.length} frames).`);
      } else {
        setRawKeypointsData([]);
        setFramesData(frames);
        onRawPointsUpdate(null);
        onFrameUpdate(frames[0]);
        setStatus(`Loaded '${word}' (${frames.length} frames).`);
      }

      setCurrentIdx(0);
      currentIdxRef.current = 0;
      setIsPlaying(true); // Autoplay so avatar is immediately moving!
    } catch (err) {
      setStatus(`Failed to load '${word}': ${err.message}`);
    }
  }, [debugSettings.relaxRight, debugSettings.relaxLeft, onFrameUpdate, onRawPointsUpdate]);

  // 3. Load Synthetic Preset
  const loadSyntheticPreset = useCallback((presetId) => {
    const preset = SYNTHETIC_PRESETS.find(p => p.id === presetId);
    if (!preset) return;

    if (preset.isAnimated) {
      // Dynamic animated wave loop
      setFramesData([]);
      setIsPlaying(true);
      setStatus(`Running live animation: ${preset.label}`);
    } else {
      setIsPlaying(false);
      const rawKps = preset.getFrame();
      const solved = solveMHRDirect(rawKps);
      setRawKeypointsData([rawKps]);
      setFramesData([solved]);
      setCurrentIdx(0);
      currentIdxRef.current = 0;
      onFrameUpdate(solved);
      onRawPointsUpdate(rawKps);
      setStatus(`Active preset: ${preset.label}`);
    }
  }, [onFrameUpdate, onRawPointsUpdate]);

  // Handle Source Selection change
  useEffect(() => {
    if (sourceType === 'lexicon') {
      loadLexiconWord(selectedWord);
    } else if (sourceType === 'synthetic') {
      loadSyntheticPreset(selectedPreset);
    }
  }, [sourceType, selectedWord, selectedPreset, loadLexiconWord, loadSyntheticPreset]);

  // 4. File Drop / Upload
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const json = JSON.parse(evt.target.result);
        if (Array.isArray(json.frames)) {
          setFramesData(json.frames);
          setCurrentIdx(0);
          currentIdxRef.current = 0;
          setStatus(`Loaded ${file.name} (${json.frames.length} frames).`);
        } else if (Array.isArray(json)) {
          // Assume raw keypoint array [[70x3], ...]
          const solved = solveMHRSequence(json);
          setRawKeypointsData(json);
          setFramesData(solved);
          setCurrentIdx(0);
          currentIdxRef.current = 0;
          setStatus(`Loaded raw mocap ${file.name} (${json.length} frames).`);
        }
      } catch (err) {
        setStatus(`Error reading JSON: ${err.message}`);
      }
    };
    reader.readAsText(file);
  };

  // 5. Playback Loop via requestAnimationFrame
  useEffect(() => {
    if (!isPlaying) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }

    lastTimeRef.current = performance.now();

    const tick = (now) => {
      // Throttle to target FPS (~25 FPS)
      const elapsed = now - lastTimeRef.current;
      const targetInterval = (1000 / 25) / speed;
      
      if (elapsed < targetInterval) {
        rafRef.current = requestAnimationFrame(tick);
        return;
      }
      
      const dt = elapsed / 1000;
      lastTimeRef.current = now;

      if (sourceType === 'synthetic') {
        const preset = SYNTHETIC_PRESETS.find(p => p.id === selectedPreset);
        if (preset && preset.isAnimated) {
          animTimeRef.current += dt * speed;
          const rawKps = preset.getFrame(animTimeRef.current);
          const solved = solveMHRDirect(rawKps);
          onFrameUpdate(solved);
          onRawPointsUpdate(rawKps);
          rafRef.current = requestAnimationFrame(tick);
          return;
        }
      }

      if (!framesData.length) return;

      let next = currentIdxRef.current + 1;
      if (next >= framesData.length) {
        if (isLooping) {
          next = 0;
        } else {
          setIsPlaying(false);
          return;
        }
      }

      currentIdxRef.current = next;
      setCurrentIdx(next);

      let frameToPlay;
      if (liveSolve && rawKeypointsData[next]) {
        frameToPlay = solveMHRDirect(rawKeypointsData[next], {
          relaxRight: debugSettings.relaxRight,
          relaxLeft: debugSettings.relaxLeft
        });
      } else if (framesData[next]) {
        frameToPlay = applyOverrides(framesData[next]);
      }

      if (frameToPlay) {
        onFrameUpdate(frameToPlay);
        if (rawKeypointsData[next]) {
          onRawPointsUpdate(rawKeypointsData[next]);
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [isPlaying, isLooping, speed, framesData, rawKeypointsData, sourceType, selectedPreset, liveSolve, debugSettings.relaxRight, debugSettings.relaxLeft, onFrameUpdate, onRawPointsUpdate]);

  const applyOverrides = useCallback((f) => {
    if (!f || !f.pose) return f;
    const clone = { ...f, pose: { ...f.pose } };
    if (debugSettings.relaxRight) {
      Object.assign(clone.pose, REST_ARM_RIGHT);
    }
    if (debugSettings.relaxLeft) {
      Object.assign(clone.pose, REST_ARM_LEFT);
    }
    return clone;
  }, [debugSettings.relaxRight, debugSettings.relaxLeft]);

  // Jump to specific frame on slider seek
  const handleSeek = (idx) => {
    if (!framesData.length) return;
    const clamped = Math.max(0, Math.min(framesData.length - 1, idx));
    setCurrentIdx(clamped);
    currentIdxRef.current = clamped;
    let frameToPlay;
    if (liveSolve && rawKeypointsData[clamped]) {
      frameToPlay = solveMHRDirect(rawKeypointsData[clamped], {
        relaxRight: debugSettings.relaxRight,
        relaxLeft: debugSettings.relaxLeft
      });
    } else {
      frameToPlay = applyOverrides(framesData[clamped]);
    }
    if (frameToPlay) {
      onFrameUpdate(frameToPlay);
      if (rawKeypointsData[clamped]) {
        onRawPointsUpdate(rawKeypointsData[clamped]);
      }
    }
  };

  const handleRecalculateLive = useCallback(() => {
    if (!rawKeypointsData.length) return;
    const fresh = solveMHRSequence(rawKeypointsData, {
      relaxRight: debugSettings.relaxRight,
      relaxLeft: debugSettings.relaxLeft
    });
    setFramesData(fresh);
    const curr = fresh[currentIdx] || fresh[0];
    if (curr) onFrameUpdate(curr);
    setStatus(`✓ Live re-calculated all ${fresh.length} frames through solver!`);
  }, [rawKeypointsData, debugSettings.relaxRight, debugSettings.relaxLeft, currentIdx, onFrameUpdate]);

  // Re-apply overrides when settings change
  useEffect(() => {
    if (framesData[currentIdx]) {
      if (liveSolve && rawKeypointsData[currentIdx]) {
        onFrameUpdate(solveMHRDirect(rawKeypointsData[currentIdx], {
          relaxRight: debugSettings.relaxRight,
          relaxLeft: debugSettings.relaxLeft
        }));
      } else {
        onFrameUpdate(applyOverrides(framesData[currentIdx]));
      }
    }
  }, [debugSettings.relaxRight, debugSettings.relaxLeft, liveSolve, applyOverrides, framesData, rawKeypointsData, currentIdx, onFrameUpdate]);

  return (
    <div style={{ background: '#0a1428', border: '1px solid #1e3a6a', borderRadius: 8, padding: 14, color: '#e0e8f8', marginTop: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, borderBottom: '1px solid #1e3a6a', paddingBottom: 8 }}>
        <h3 style={{ margin: 0, color: '#4da6ff', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>🛠️</span> Rapid Mocap Testbench & Visualizer
        </h3>
        <span style={{ fontSize: '0.75rem', background: '#102544', padding: '2px 8px', borderRadius: 4, color: '#88bbff' }}>
          Hot-Reload: 50ms
        </span>
      </div>

      {/* Row 1: Mocap Source Selection */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10, marginBottom: 12 }}>
        <div>
          <label style={{ fontSize: '0.75rem', color: '#88aaff', display: 'block', marginBottom: 4 }}>Source Mode</label>
          <select
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            style={{ width: '100%', padding: '6px', background: '#07101e', border: '1px solid #2a4f85', color: '#fff', borderRadius: 4 }}
          >
            <option value="lexicon">Dictionary Sign (Offline MHR)</option>
            <option value="synthetic">Mathematical Preset Poses</option>
            <option value="file">Custom JSON File Upload</option>
          </select>
        </div>

        {sourceType === 'lexicon' && (
          <div>
            <label style={{ fontSize: '0.75rem', color: '#88aaff', display: 'block', marginBottom: 4 }}>Select Saved Sign</label>
            <select
              value={selectedWord}
              onChange={(e) => setSelectedWord(e.target.value)}
              style={{ width: '100%', padding: '6px', background: '#07101e', border: '1px solid #2a4f85', color: '#fff', borderRadius: 4 }}
            >
              {lexiconWords.map(w => (
                <option key={w} value={w}>{w}</option>
              ))}
            </select>
          </div>
        )}

        {sourceType === 'synthetic' && (
          <div>
            <label style={{ fontSize: '0.75rem', color: '#88aaff', display: 'block', marginBottom: 4 }}>Mathematical Benchmark Pose</label>
            <select
              value={selectedPreset}
              onChange={(e) => setSelectedPreset(e.target.value)}
              style={{ width: '100%', padding: '6px', background: '#07101e', border: '1px solid #2a4f85', color: '#fff', borderRadius: 4 }}
            >
              {SYNTHETIC_PRESETS.map(p => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>
        )}

        {sourceType === 'file' && (
          <div>
            <label style={{ fontSize: '0.75rem', color: '#88aaff', display: 'block', marginBottom: 4 }}>Upload Mocap JSON</label>
            <input
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              style={{ fontSize: '0.75rem', color: '#ccc' }}
            />
          </div>
        )}
      </div>

      {/* Row 2: Timeline Controls & Scrubber */}
      <div style={{ background: '#07101e', padding: 10, borderRadius: 6, marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            style={{
              padding: '6px 14px',
              background: isPlaying ? '#d32f2f' : '#2e7d32',
              border: 'none',
              borderRadius: 4,
              color: '#fff',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            {isPlaying ? '⏸ Pause' : '▶ Play'}
          </button>

          <button
            onClick={() => handleSeek(currentIdx - 1)}
            disabled={isPlaying || currentIdx <= 0}
            style={{ padding: '6px 10px', background: '#1e3a6a', border: 'none', borderRadius: 4, color: '#fff', cursor: 'pointer' }}
          >
            ◀ Step
          </button>

          <button
            onClick={() => handleSeek(currentIdx + 1)}
            disabled={isPlaying || currentIdx >= framesData.length - 1}
            style={{ padding: '6px 10px', background: '#1e3a6a', border: 'none', borderRadius: 4, color: '#fff', cursor: 'pointer' }}
          >
            Step ▶
          </button>

          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={isLooping}
              onChange={(e) => setIsLooping(e.target.checked)}
            />
            Loop
          </label>

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: '0.75rem', color: '#88aaff' }}>Speed:</span>
            {[0.25, 0.5, 1.0].map(s => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                style={{
                  padding: '2px 6px',
                  fontSize: '0.75rem',
                  background: speed === s ? '#4da6ff' : '#102544',
                  color: speed === s ? '#000' : '#fff',
                  border: 'none',
                  borderRadius: 3,
                  cursor: 'pointer'
                }}
              >
                {s}×
              </button>
            ))}
          </div>
        </div>

        {/* Scrubber slider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '0.75rem', color: '#88aaff', minWidth: 70 }}>
            Frame {framesData.length ? currentIdx : 0} / {Math.max(0, framesData.length - 1)}
          </span>
          <input
            type="range"
            min={0}
            max={Math.max(0, framesData.length - 1)}
            value={currentIdx}
            onChange={(e) => handleSeek(parseInt(e.target.value, 10))}
            style={{ flex: 1 }}
            disabled={!framesData.length || isPlaying}
          />
        </div>
      </div>

      {/* Row 3: 3D Visualizer & Coordinate Overrides */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, fontSize: '0.8rem', alignItems: 'center' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: '#00ff88', fontWeight: 'bold' }}>
          <input
            type="checkbox"
            checked={debugSettings.showSkeleton}
            onChange={(e) => onSettingsChange({ ...debugSettings, showSkeleton: e.target.checked })}
          />
          Show 3D Skeleton (Stick Figure)
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={debugSettings.sideBySide}
            onChange={(e) => onSettingsChange({ ...debugSettings, sideBySide: e.target.checked })}
          />
          Side-by-Side (vs Overlay)
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={debugSettings.flipX}
            onChange={(e) => onSettingsChange({ ...debugSettings, flipX: e.target.checked })}
          />
          Flip X
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={debugSettings.flipY}
            onChange={(e) => onSettingsChange({ ...debugSettings, flipY: e.target.checked })}
          />
          Flip Y
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={debugSettings.flipZ}
            onChange={(e) => onSettingsChange({ ...debugSettings, flipZ: e.target.checked })}
          />
          Flip Z
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: '#ffbb33', fontWeight: 'bold' }}>
          <input
            type="checkbox"
            checked={debugSettings.relaxRight}
            onChange={(e) => onSettingsChange({ ...debugSettings, relaxRight: e.target.checked })}
          />
          Rest Unseen Right Arm
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: '#ffbb33', fontWeight: 'bold' }}>
          <input
            type="checkbox"
            checked={debugSettings.relaxLeft}
            onChange={(e) => onSettingsChange({ ...debugSettings, relaxLeft: e.target.checked })}
          />
          Rest Unseen Left Arm
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: '#ff9900', fontWeight: 'bold' }}>
          <input
            type="checkbox"
            checked={liveSolve}
            onChange={(e) => setLiveSolve(e.target.checked)}
          />
          ⚡ Live Calculation (solveMHRDirect)
        </label>

        {rawKeypointsData.length > 0 && (
          <button
            onClick={handleRecalculateLive}
            style={{
              padding: '3px 9px',
              background: '#ff9900',
              color: '#000',
              fontWeight: 'bold',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: '0.75rem'
            }}
          >
            🔄 Re-Calculate All ({rawKeypointsData.length} pts)
          </button>
        )}
      </div>

      {status && (
        <div style={{ marginTop: 8, fontSize: '0.75rem', color: '#88aaff' }}>
          {status}
        </div>
      )}
    </div>
  );
}
