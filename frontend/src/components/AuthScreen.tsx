import { useState } from "react";
import { ApiError, AuthUser, login, signup } from "../api";

export default function AuthScreen({ onAuthed }: { onAuthed: (user: AuthUser) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function switchMode(next: "login" | "signup") {
    setMode(next);
    setError(null);
    setNotice(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      if (mode === "signup") {
        const result = await signup(email.trim(), password);
        setNotice(result.message);
        setMode("login");
        setPassword("");
      } else {
        const user = await login(email.trim(), password);
        onAuthed(user);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="picker-intro">
      <h1>{mode === "login" ? "Welcome back." : "Ask to come in."}</h1>
      <p>
        {mode === "login"
          ? "Sign in to continue the conversations you've started."
          : "Create an account — an admin will need to approve it before you can sign in."}
      </p>

      {notice && <div className="auth-notice">{notice}</div>}
      {error && <div className="error-banner">{error}</div>}

      <form className="create-form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="auth-email">Email</label>
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "signup" ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {mode === "signup" && (
            <span className="field-hint">At least 8 characters, with an uppercase letter, a lowercase letter, and a number.</span>
          )}
        </div>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>

      <div className="divider-label">or</div>

      {mode === "login" ? (
        <p>
          New here?{" "}
          <button className="btn--text" type="button" onClick={() => switchMode("signup")}>
            Create an account
          </button>
        </p>
      ) : (
        <p>
          Already approved?{" "}
          <button className="btn--text" type="button" onClick={() => switchMode("login")}>
            Sign in instead
          </button>
        </p>
      )}
    </div>
  );
}
