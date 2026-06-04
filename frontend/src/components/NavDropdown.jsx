// Hover-activated dropdown for nav buttons. Each sub-item is an anchor
// link to a section ID inside the destination page, so clicking jumps
// directly to that part of the page.
import { NavLink, useLocation, useNavigate } from 'react-router-dom';

export default function NavDropdown({ to, label, sections }) {
  const location = useLocation();
  const navigate = useNavigate();
  const isActive = location.pathname === to;

  // Clicking a sub-item: navigate to /to#section. If we're already there,
  // jump via scrollIntoView; otherwise let react-router handle the route
  // change first and the useEffect on the page does the scroll.
  const handleSub = (e, sectionId) => {
    e.preventDefault();
    if (location.pathname === to) {
      const el = document.getElementById(sectionId);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      navigate(`${to}#${sectionId}`);
    }
  };

  return (
    <div className={`nav-item ${isActive ? 'active' : ''}`}>
      <NavLink to={to} className="nav-button">{label}</NavLink>
      <div className="nav-dropdown">
        {sections.map((s) => (
          <a key={s.id} href={`${to}#${s.id}`} onClick={(e) => handleSub(e, s.id)}>
            {s.label}
          </a>
        ))}
      </div>
    </div>
  );
}
