import React from 'react';

export default function GlossPanel({ gloss, stats, activeTokenIdx }) {
  if (!gloss) {
    return (
      <div className="card">
        <h2>Gloss</h2>
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
          Translate a sentence to see its ASL gloss here. Words found in the
          <b> lexicon</b> use their real ASL animation; unknown words are
          <b> fingerspelled letter-by-letter</b>.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Gloss</h2>
      <div style={{ fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 14 }}>
        {gloss.gloss_string || '(empty)'}
      </div>

      <div className="gloss-row">
        {(gloss.tokens || []).map((t, i) => {
          const isLex = t.source === 'lexicon';
          const isSpell = t.source === 'fingerspell';
          return (
            <span
              key={i}
              className={
                'gloss-chip'
                + (isSpell ? ' fingerspell' : '')
                + (isLex ? ' lexicon' : '')
                + (i === activeTokenIdx ? ' active' : '')
              }
              title={isLex ? 'lexicon hit' : (isSpell ? 'fingerspelled' : t.kind)}
            >
              {isLex ? '✓ ' : ''}{t.token}
            </span>
          );
        })}
      </div>

      {stats ? (
        <>
          <div className="stat-grid">
            <div className="stat"><div className="l">Frames</div><div className="v">{stats.total_frames}</div></div>
            <div className="stat"><div className="l">Duration</div><div className="v">{stats.total_seconds}s</div></div>
            <div className="stat"><div className="l">Tokens</div><div className="v">{stats.tokens}</div></div>
            <div className="stat"><div className="l">Lexicon</div><div className="v">{stats.tokens_found}</div></div>
            <div className="stat"><div className="l">Spelled</div><div className="v">{stats.tokens_fingerspelled}</div></div>
          </div>
          {stats.lexicon ? (
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 8 }}>
              Lexicon loaded: <b style={{ color: 'var(--good)' }}>{stats.lexicon.total_cached}</b> signs
              ({stats.lexicon.words} words + {stats.lexicon.fixed} fixed +
              {stats.lexicon.fingerspelling} fingerspell letters).
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
