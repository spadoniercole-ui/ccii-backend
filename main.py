"use client";

import { useState } from "react";
import SuperAdminDashboard from "../components/SuperAdminDashboard";

const API = "https://cciiplatform-production.up.railway.app";

export default function Page() {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const login = async () => {
    try {
      const res = await fetch(`${API}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ username, password })
      });

      if (res.status !== 200) {
        alert("Errore login");
        return;
      }

      const data = await res.json();
      const tokenValue = data.access_token || data.token;

      // Gestione sicura del token
      if (tokenValue === "token_superadmin_fisso") {
        setToken(tokenValue);
        setRole("SUPER_ADMIN");
      } else if (tokenValue && typeof tokenValue === 'string' && tokenValue.includes('.')) {
        const payload = JSON.parse(atob(tokenValue.split(".")[1]));
        setToken(tokenValue);
        setRole(payload.role);
      } else {
        alert("Formato token non riconosciuto");
      }
    } catch (err) {
      console.error(err);
      alert("Errore chiamata API");
    }
  };

  if (!token) {
    return (
      <div style={{ padding: 40 }}>
        <h1>Login CCII</h1>

        <input
          placeholder="Username"
          onChange={(e) => setUsername(e.target.value)}
        />

        <br /><br />

        <input
          type="password"
          placeholder="Password"
          onChange={(e) => setPassword(e.target.value)}
        />

        <br /><br />

        <button onClick={login}>Login</button>
      </div>
    );
  }

  if (role === "SUPER_ADMIN") {
    return <SuperAdminDashboard token={token} />;
  }

  return <h1>Utente autenticato</h1>;
}
