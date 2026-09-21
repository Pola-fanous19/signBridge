import React from 'react';

export default function HelpCard() {
  return (
    <div className="card">
      <h2>How it works</h2>
      <ol className="help-list">
        <li>Type any English sentence.</li>
        <li>Pick a <b>gloss backend</b>: rule-based (offline) or <b>Gemini API</b>.
            When Gemini is selected, an icon shows if the API is <span style={{color:'var(--good)'}}>connected</span>.</li>
        <li>Words found in the <b>lexicon</b> (words/ &amp; fixed/) play their real ASL animation. Everything else is <b>fingerspelled letter-by-letter</b> using anatomically correct handshapes.</li>
        <li>Use the <b>Avatar speed</b> slider to adjust playback speed from 0.25× (slow, for learning) up to 3× (fast).</li>
        <li>The 3D avatar uses <b>MediaPipe topology</b> — 21 landmarks per hand — with tapered fingers, real fingernails, and a thickened palm mesh for realistic sign reading.</li>
        <li>Facial features (raised eyebrows) act as <b>non-manual markers</b> for questions.</li>
      </ol>
    </div>
  );
}
