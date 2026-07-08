import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/useAuth";

export default function Login() {
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    clearError();
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch {
      // error already set in store
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo & Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-500 bg-opacity-20 border border-blue-400 border-opacity-30 mb-4">
            <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">VayuShield AI</h1>
          <p className="text-blue-300 text-sm mt-1">Urban Air Quality Intelligence Platform</p>
        </div>

        {/* Card */}
        <div className="bg-white bg-opacity-5 backdrop-blur-sm border border-white border-opacity-10 rounded-2xl p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-white mb-6">Sign in to your account</h2>

          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-red-500 bg-opacity-15 border border-red-400 border-opacity-30 text-red-300 text-sm flex items-start gap-2">
              <svg className="w-4 h-4 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-blue-200 mb-1.5">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-lg bg-white bg-opacity-10 border border-white border-opacity-15 text-white placeholder-blue-300 placeholder-opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent transition"
                placeholder="you@vayushield.local"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-blue-200 mb-1.5">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-lg bg-white bg-opacity-10 border border-white border-opacity-15 text-white placeholder-blue-300 placeholder-opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent transition"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 rounded-lg font-semibold text-white bg-blue-500 hover:bg-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-transparent disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Signing in…
                </span>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-blue-400 text-opacity-60">
            Contact your system administrator for access
          </p>
        </div>

        {/* AQI color band strip */}
        <div className="mt-6 flex rounded-full overflow-hidden h-1.5 opacity-40">
          <div className="flex-1 bg-green-400" />
          <div className="flex-1 bg-lime-400" />
          <div className="flex-1 bg-yellow-400" />
          <div className="flex-1 bg-orange-400" />
          <div className="flex-1 bg-red-500" />
          <div className="flex-1 bg-purple-700" />
        </div>
        <p className="text-center text-xs text-blue-500 text-opacity-40 mt-2">
          Good · Satisfactory · Moderate · Poor · Very Poor · Severe
        </p>
      </div>
    </div>
  );
}
