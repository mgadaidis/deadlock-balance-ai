// Small ornamental utilities used by every page so the bureau aesthetic
// is consistent and individual page files stay focused on data.

// Roman-numeral marker for a section. Use sparingly — only on top-level
// section headers, not nested ones.
const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'];

export function SectionHead({ index, title, sub, right }) {
  return (
    <div className="section-head">
      <div className="title-block">
        {index != null && <span className="numeral">{ROMAN[index] || '·'}</span>}
        <div>
          <h2>{title}</h2>
          {sub && <span className="sub">{sub}</span>}
        </div>
      </div>
      {right}
    </div>
  );
}

// Gilt corner ornaments — drop inside a .card to get the brass corners.
// We render an SVG mark in the top-left and a 180°-rotated copy in the
// bottom-right, both small enough to read as bracket-type ornaments.
function CornerOrnament() {
  return (
    <svg viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <path d="M 1 1 L 8 1 L 8 2.5 L 2.5 2.5 L 2.5 8 L 1 8 Z" fill="currentColor" />
      <path d="M 5 5 L 11 5 L 11 6 L 6 6 L 6 11 L 5 11 Z" fill="currentColor" opacity="0.6" />
    </svg>
  );
}

export function GiltCorners() {
  return (
    <>
      <span className="gilt-tl"><CornerOrnament /></span>
      <span className="gilt-br"><CornerOrnament /></span>
    </>
  );
}

// Ornamental horizontal divider used between major content blocks inside
// a section (e.g. between the win-rate chart and an explanatory note).
export function Divider() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '1rem',
      margin: '1.4rem 0', color: 'var(--c-gilt-dim)',
    }} aria-hidden>
      <span style={{ flex: 1, height: 1, background: 'linear-gradient(90deg, transparent, currentColor)' }} />
      <span style={{ fontFamily: 'var(--f-display)', fontSize: '0.7rem', letterSpacing: '0.4em' }}>✦</span>
      <span style={{ flex: 1, height: 1, background: 'linear-gradient(90deg, currentColor, transparent)' }} />
    </div>
  );
}
