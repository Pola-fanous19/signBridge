// SignBridge v4 - main React app.
//
// Simplified from v3:
//   * REST only (WebSocket + batch mode removed)
//   * Adjustable avatar playback speed
//   * Gemini API connection indicator icon
//   * Full lexicon (words / fixed / fingerspelling) is served from the backend

import React, { useCallback, useEffect, useRef, useState } from 'react';

import GlossPanel    from './components/GlossPanel.jsx';
import AvatarCard    from './components/AvatarCard.jsx';
import HelpCard      from './components/HelpCard.jsx';
import GeminiStatus  from './components/GeminiStatus.jsx';
import WebcamCapture from './components/WebcamCapture.jsx';
import MocapDebugger from './components/MocapDebugger.jsx';

import { PosePlayer }    from './lib/posePlayer.js';
import { translateREST } from './lib/api.js';
import { neutralFrame }  from './lib/schema.js';
import { frameForLetter } from './lib/fingerspell.js';
import { mapMhrToVRM, mapMhrSequence } from './lib/mhrMapper.js';

const DEFAULT_SENTENCE = 'Are you going to the store tomorrow?';

function buildLocalFingerspellClip(text, fps = 30, hold = 10, gap = 4) {
  const letters = text.toUpperCase().split('').filter((c) => /[A-Z]/.test(c));
  const frames = [];
  const tokens = [];
  const perTokenFrames = [];
  let cursor = 0;

  for (const letter of letters) {
    const key = frameForLetter(letter);
    const start = cursor;
    for (let i = 0; i < hold; i++) frames.push({ ...key });
    cursor += hold;
    for (let i = 0; i < gap; i++) frames.push(neutralFrame());
    cursor += gap;
    tokens.push({ token: letter, kind: 'fingerspell', source: 'fingerspell' });
    perTokenFrames.push({ start, end: start + hold - 1, token: letter });
  }
  if (!frames.length) frames.push(neutralFrame());
  return { clip: { frames, fps }, tokens, perTokenFrames };
}

function buildFrameIndex(gloss, poseFrames) {
  if (!gloss?.tokens?.length || !poseFrames?.length) return () => ({});
  const totalFrames = poseFrames.length;
  const tokens = gloss.tokens;
  let cursor = 0;
  const ranges = tokens.map((t) => {
    const count = Number.isFinite(t.frames)
      ? t.frames
      : Math.max(1, Math.floor(totalFrames / tokens.length));
    const start = cursor;
    const end = Math.min(totalFrames - 1, cursor + count - 1);
    cursor = end + 1;
    return { start, end, token: t };
  });
  if (ranges.length) ranges[ranges.length - 1].end = totalFrames - 1;

  return (frameIdx) => {
    for (let i = 0; i < ranges.length; i++) {
      const r = ranges[i];
      if (frameIdx >= r.start && frameIdx <= r.end) {
        let letter = null;
        // Fingerspelled tokens: figure out which letter is displaying
        if ((r.token.source === 'fingerspell' || r.token.kind === 'fingerspell')
            && r.token.token?.length) {
          const word = r.token.token.replace(/[^A-Za-z]/g, '');
          if (word.length) {
            const span = (r.end - r.start + 1) / word.length;
            const li = Math.min(word.length - 1, Math.floor((frameIdx - r.start) / span));
            letter = word[li].toUpperCase();
          }
        }
        return { tokenIndex: i, token: r.token.token, letter };
      }
    }
    return {};
  };
}

export default function App() {
  const [text, setText]     = useState(DEFAULT_SENTENCE);
  const [webcamMode, setWebcamMode] = useState(false);
  const [backend, setBackend] = useState('rule');
  const [server, setServer] = useState('');
  const [busy, setBusy]     = useState(false);
  const [error, setError]   = useState('');
  const [gloss, setGloss]   = useState(null);
  const [stats, setStats]   = useState(null);


  const [frameIndex, setFrameIndex] = useState(0);
  const [frameTotal, setFrameTotal] = useState(0);
  const [currentLetter, setCurrentLetter] = useState(null);
  const [currentToken,  setCurrentToken]  = useState(null);
  const [activeTokenIdx, setActiveTokenIdx] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed]     = useState(1.0);

  const [debugMode, setDebugMode] = useState(false);
  const [rawPoints, setRawPoints] = useState(null);
  const [debugSettings, setDebugSettings] = useState({
    showSkeleton: true,
    sideBySide: true,
    flipX: false,
    flipY: true,
    flipZ: true,
  });

  const frameRef  = useRef(neutralFrame());
  const playerRef = useRef(null);
  const indexerRef = useRef(() => ({}));

  if (!playerRef.current) playerRef.current = new PosePlayer();

  useEffect(() => {
    const player = playerRef.current;
    player.onFrame = (frame, idx, total) => {
      frameRef.current = frame;
      setFrameIndex(idx);
      setFrameTotal(total);
      const info = indexerRef.current(idx);
      setCurrentLetter(info.letter || null);
      setCurrentToken(info.token || null);
      setActiveTokenIdx(typeof info.tokenIndex === 'number' ? info.tokenIndex : -1);
    };
    player.onEnd = () => setPlaying(false);
    return () => player.stop();
  }, []);

  // Push speed changes to the player instance immediately.
  useEffect(() => {
    if (playerRef.current) playerRef.current.setSpeed(speed);
  }, [speed]);

  const runLocalFallback = useCallback((reason) => {
    if (reason) setError(`${reason} — using local fingerspelling fallback.`);
    const { clip, tokens, perTokenFrames } = buildLocalFingerspellClip(text);
    setGloss({ gloss_string: tokens.map((t) => t.token).join(' '), tokens });
    setStats({
      total_frames: clip.frames.length,
      total_seconds: (clip.frames.length / clip.fps).toFixed(2),
      tokens: tokens.length,
      tokens_found: 0,
      tokens_fingerspelled: tokens.length,
      missing_tokens: [],
    });
    indexerRef.current = (idx) => {
      for (let i = 0; i < perTokenFrames.length; i++) {
        const r = perTokenFrames[i];
        if (idx >= r.start && idx <= r.end) {
          return { tokenIndex: i, token: r.token, letter: r.token };
        }
      }
      return {};
    };
    playerRef.current.load(clip);
    playerRef.current.setSpeed(speed);
    setFrameTotal(clip.frames.length);
    setPlaying(true);
    playerRef.current.play();
  }, [text, speed]);

  const handleTranslate = useCallback(async () => {
    if (!text.trim()) return;
    setBusy(true); setError('');
    setGloss(null); setStats(null);
    setActiveTokenIdx(-1); setCurrentLetter(null); setCurrentToken(null);

    try {
      const r = await translateREST({ text, backend, serverUrl: server });
      setGloss(r.gloss);
      setStats(r.stats);
      indexerRef.current = buildFrameIndex(r.gloss, r.pose?.frames || []);
      playerRef.current.load(r.pose);
      playerRef.current.setSpeed(speed);
      setFrameTotal(r.pose?.frames?.length || 0);
      setPlaying(true);
      playerRef.current.play();
    } catch (e) {
      runLocalFallback(e.message || 'Backend unreachable');
    } finally {
      setBusy(false);
    }
  }, [text, backend, server, runLocalFallback, speed]);

  const handleReplay = useCallback(() => {
    if (!playerRef.current.frames.length) return;
    setPlaying(true);
    playerRef.current.play();
  }, []);

  const handleSeek = useCallback((idx) => {
    playerRef.current.stop();
    setPlaying(false);
    playerRef.current.seek(idx);
  }, []);

  // Live per-keystroke letter preview (before pressing Translate).
  useEffect(() => {
    if (busy || playing) return;
    if (playerRef.current.frames.length) return;
    const letters = text.toUpperCase().replace(/[^A-Z]/g, '');
    if (!letters.length) {
      frameRef.current = neutralFrame();
      setCurrentLetter(null);
      return;
    }
    const last = letters[letters.length - 1];
    frameRef.current = frameForLetter(last);
    setCurrentLetter(last);
  }, [text, busy, playing]);

  // Callbacks for the debugger
  const handleFrameUpdate = useCallback((frame) => {
    frameRef.current = frame;
  }, []);

  const handleRawPointsUpdate = useCallback((points) => {
    setRawPoints(points);
  }, []);

  return (
    <>
      <header className="app-header">
        <h1>SignBridge</h1>
        <p className="subtitle">English → ASL gloss → 3D avatar</p>
        <span className="tag">v4 · lexicon + Gemini</span>
      </header>

      <main>
        {/* Rapid Iteration Mode Switcher */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginBottom: 20 }}>
          <button
            className={!debugMode ? 'primary' : 'secondary'}
            onClick={() => setDebugMode(false)}
            style={{ flex: 1, padding: '10px 16px', fontWeight: 'bold' }}
          >
            💬 English → Sign Translator
          </button>
          <button
            className={debugMode ? 'primary' : 'secondary'}
            onClick={() => {
              setDebugMode(true);
              if (playing) {
                playerRef.current.stop();
                setPlaying(false);
              }
            }}
            style={{
              flex: 1,
              padding: '10px 16px',
              fontWeight: 'bold',
              background: debugMode ? '#ff9800' : undefined,
              color: debugMode ? '#000' : undefined,
              borderColor: '#ff9800'
            }}
          >
            🛠️ Rapid Mocap Debugger & 3D Skeleton
          </button>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}

        {/* 1. Debugger Panel (when active) */}
        {debugMode && (
          <MocapDebugger
            onFrameUpdate={handleFrameUpdate}
            onRawPointsUpdate={handleRawPointsUpdate}
            debugSettings={debugSettings}
            onSettingsChange={setDebugSettings}
          />
        )}

        {/* 2. Normal Translation Input (when not in debugger) */}
        {!debugMode && (
          <section className="card">
            <h2>Input</h2>
            <label className="field-label" htmlFor="text">English</label>
            <textarea
              id="text"
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Type any English sentence — words in the lexicon are signed, unknown words are fingerspelled."
            />

            <div className="controls">
              <label className="field">
                <span>Gloss backend</span>
                <select value={backend} onChange={(e) => setBackend(e.target.value)}>
                  <option value="rule">Rule-based (offline)</option>
                  <option value="gemini">Gemini API</option>
                </select>
              </label>
              <label className="field">
                <span>Server URL (blank = local)</span>
                <input
                  type="text"
                  value={server}
                  placeholder="http://localhost:8000"
                  onChange={(e) => setServer(e.target.value)}
                />
              </label>
            </div>

            {/* Gemini connection status indicator */}
            <GeminiStatus backend={backend} serverUrl={server} />

            <div className="controls-row">
              <button onClick={handleTranslate} disabled={busy}>
                {busy ? 'Translating…' : 'Translate → Sign'}
              </button>
              <button className="secondary" onClick={() => runLocalFallback('')}>
                Local fingerspell only
              </button>
              <button
                className="secondary"
                style={{ borderColor: webcamMode ? '#88aaff' : undefined, color: webcamMode ? '#88aaff' : undefined }}
                onClick={() => {
                  setWebcamMode(!webcamMode);
                  if (playing) {
                    playerRef.current.stop();
                    setPlaying(false);
                  }
                }}
              >
                {webcamMode ? 'Disable Webcam Mimicry' : 'Enable Webcam Mimicry'}
              </button>
            </div>
          </section>
        )}

        <AvatarCard
          frameRef={frameRef}
          currentLetter={currentLetter}
          currentToken={currentToken}
          frameIndex={frameIndex}
          frameTotal={frameTotal}
          playing={playing}
          onReplay={handleReplay}
          onSeek={handleSeek}
          speed={speed}
          onSpeedChange={setSpeed}
          rawPoints={rawPoints}
          debugSettings={debugSettings}
        />

        {!debugMode && (
          <>
            <GlossPanel gloss={gloss} stats={stats} activeTokenIdx={activeTokenIdx} />
            <HelpCard />
          </>
        )}
        
        {webcamMode && (
          <WebcamCapture 
            onHolisticResults={(results) => {
              // Instantly pipe webcam results to the Avatar's frameRef for real-time rendering
              // We pass the raw results object to preserve any minified keys (ea, za) 
              // that Mediapipe uses for poseWorldLandmarks in production builds.
              frameRef.current = {
                isHolisticResult: true,
                ...results
              };
            }} 
            onMhrReceived={async (frames, recordedWord) => {
              const signName = (recordedWord || 'RECORDED_SIGN').toUpperCase();
              const mappedFrames = mapMhrSequence(frames);

              // Persist permanently to backend lexicon
              try {
                await fetch('/api/save-sign', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ 
                    word: signName, 
                    frames: mappedFrames,
                    rawFrames: frames
                  })
                });
                console.log(`[+] Sign '${signName}' attached to dictionary!`);
              } catch (err) {
                console.warn('Failed to save to local lexicon:', err);
              }

              const fakeGloss = {
                gloss_string: signName,
                tokens: [{ token: signName, kind: 'sign', frames: mappedFrames.length }]
              };
              setGloss(fakeGloss);
              setStats({ total_frames: mappedFrames.length, total_seconds: (mappedFrames.length / 10).toFixed(2), tokens: 1 });
              
              indexerRef.current = buildFrameIndex(fakeGloss, mappedFrames);
              
              playerRef.current.load({ frames: mappedFrames, fps: 10 });
              playerRef.current.setSpeed(speed);
              setFrameTotal(mappedFrames.length);
              setPlaying(true);
              playerRef.current.play();
              
              setWebcamMode(false);
            }}
          />
        )}
      </main>
    </>
  );
}
