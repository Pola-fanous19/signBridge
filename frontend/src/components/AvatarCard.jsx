import React from 'react';
import AvatarScene from './AvatarScene.jsx';

// Speed presets available in the UI.
const SPEED_PRESETS = [
  { label: '0.25×', value: 0.25 },
  { label: '0.5×',  value: 0.5  },
  { label: '0.75×', value: 0.75 },
  { label: '1×',    value: 1.0  },
  { label: '1.5×',  value: 1.5  },
  { label: '2×',    value: 2.0  },
];

export default function AvatarCard({
  frameRef, currentLetter, currentToken, frameIndex, frameTotal,
  playing, onReplay, onSeek, speed, onSpeedChange,
  rawPoints, debugSettings
}) {
  const pct = frameTotal > 0 ? (frameIndex / (frameTotal - 1)) * 100 : 0;

  return (
    <div className="card avatar-card">
      <h2>Avatar</h2>
      <div className="avatar-canvas-wrap">
        <AvatarScene
          frameRef={frameRef}
          rawPoints={rawPoints}
          debugSettings={debugSettings}
        />

        {currentLetter ? (
          <div className="overlay-letter">
            <div className="k">LETTER</div>
            <div className="v">{currentLetter}</div>
          </div>
        ) : null}

        {currentToken ? (
          <div className="overlay-token">
            signing <b>{currentToken}</b>
          </div>
        ) : null}

        <div className="overlay-speed-badge">Speed · {speed.toFixed(2)}×</div>
      </div>

      <div className="progress">
        <div style={{ width: `${pct}%` }} />
      </div>
      <div className="progress-meta">
        <span>{frameIndex} / {Math.max(0, frameTotal - 1)} frames</span>
        <span>{playing ? '▶ playing' : '⏸ paused'}</span>
      </div>

      <div className="controls-row">
        <button className="secondary" onClick={onReplay} disabled={!frameTotal}>
          ⟳ Replay
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(0, frameTotal - 1)}
          value={frameIndex}
          onChange={(e) => onSeek(parseInt(e.target.value, 10))}
          style={{ flex: 1 }}
          disabled={!frameTotal}
        />
      </div>

      {/* Avatar speed control */}
      <div className="speed-control">
        <div className="speed-header">
          <span className="speed-label">Avatar speed</span>
          <span className="speed-value">{speed.toFixed(2)}×</span>
        </div>
        <input
          type="range"
          min={0.25}
          max={3.0}
          step={0.05}
          value={speed}
          onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
          className="speed-slider"
        />
        <div className="speed-presets">
          {SPEED_PRESETS.map((p) => (
            <button
              key={p.value}
              className={'preset' + (Math.abs(speed - p.value) < 0.01 ? ' active' : '')}
              onClick={() => onSpeedChange(p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
