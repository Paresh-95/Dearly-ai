import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useMatch, useNavigate } from "react-router-dom";
import { AuthUser, logout, me } from "./api";
import AddMemoryPage from "./components/AddMemoryPage";
import AddPersonPage from "./components/AddPersonPage";
import AdminPanel from "./components/AdminPanel";
import AuthScreen from "./components/AuthScreen";
import CallPanel from "./components/CallPanel";
import ChatHistoryPage from "./components/ChatHistoryPage";
import ChatHistorySessionPage from "./components/ChatHistorySessionPage";
import CreatePersonaPage from "./components/CreatePersonaPage";
import Logo from "./components/Logo";
import MemoriesListPage from "./components/MemoriesListPage";
import PersonaLayout from "./components/PersonaLayout";
import PersonaListPage from "./components/PersonaListPage";
import PersonaSettingsPage from "./components/PersonaSettingsPage";
import PeopleListPage from "./components/PeopleListPage";
import VoicePanel from "./components/VoicePanel";
import "./styles.css";

type Status = "checking" | "anonymous" | "authenticated";

export default function App() {
  const [status, setStatus] = useState<Status>("checking");
  const [user, setUser] = useState<AuthUser | null>(null);
  const navigate = useNavigate();
  const personaMatch = useMatch("/personas/:personaId/*");
  const personaId = personaMatch?.params.personaId;

  useEffect(() => {
    me()
      .then((u) => {
        setUser(u);
        setStatus(u ? "authenticated" : "anonymous");
      })
      .catch(() => setStatus("anonymous"));
  }, []);

  async function handleLogout() {
    await logout();
    setUser(null);
    setStatus("anonymous");
    navigate("/");
  }

  if (status === "checking") {
    return <div className="app-shell" />;
  }

  return (
    <div className={`app-shell ${status === "authenticated" ? "app-shell--wide" : ""}`}>
      <header className="app-header">
        <Logo />
        {status === "anonymous" ? (
          <span className="app-header__tagline">a quiet place to talk</span>
        ) : (
          <span className="app-header__tagline">
            {personaId && (
              <>
                <nav className="header-tab-nav">
                  <NavLink
                    className={({ isActive }) => `header-tab-nav__item ${isActive ? "header-tab-nav__item--active" : ""}`}
                    to={`/personas/${personaId}/memories`}
                  >
                    Memories
                  </NavLink>
                  <NavLink
                    className={({ isActive }) => `header-tab-nav__item ${isActive ? "header-tab-nav__item--active" : ""}`}
                    to={`/personas/${personaId}/people`}
                  >
                    People
                  </NavLink>
                  <NavLink
                    className={({ isActive }) => `header-tab-nav__item ${isActive ? "header-tab-nav__item--active" : ""}`}
                    to={`/personas/${personaId}/voice`}
                  >
                    Voice samples
                  </NavLink>
                  <NavLink
                    className={({ isActive }) => `header-tab-nav__item ${isActive ? "header-tab-nav__item--active" : ""}`}
                    to={`/personas/${personaId}/call`}
                  >
                    Call
                  </NavLink>
                  <NavLink
                    className={({ isActive }) => `header-tab-nav__item ${isActive ? "header-tab-nav__item--active" : ""}`}
                    to={`/personas/${personaId}/settings`}
                  >
                    Settings
                  </NavLink>
                </nav>
                <span className="header-divider" />
              </>
            )}
            <span className="app-header__actions">
              {user?.is_admin && (
                <Link className="btn--text" to="/admin">
                  Admin
                </Link>
              )}
              <button className="btn btn--quiet btn--sm" onClick={handleLogout}>
                Log out
              </button>
            </span>
          </span>
        )}
      </header>

      {status === "anonymous" ? (
        <AuthScreen
          onAuthed={(u) => {
            setUser(u);
            setStatus("authenticated");
            navigate("/");
          }}
        />
      ) : (
        <Routes>
          <Route path="/" element={<PersonaListPage />} />
          <Route path="/new" element={<CreatePersonaPage />} />
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/personas/:personaId" element={<PersonaLayout />}>
            <Route index element={<Navigate to="call" replace />} />
            <Route path="memories" element={<MemoriesListPage />} />
            <Route path="memories/new" element={<AddMemoryPage />} />
            <Route path="people" element={<PeopleListPage />} />
            <Route path="people/new" element={<AddPersonPage />} />
            <Route path="voice" element={<VoicePanel />} />
            <Route path="call" element={<CallPanel />} />
            <Route path="history" element={<ChatHistoryPage />} />
            <Route path="history/:sessionId" element={<ChatHistorySessionPage />} />
            <Route path="settings" element={<PersonaSettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      )}
    </div>
  );
}
