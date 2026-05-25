import React, { useEffect, useState } from 'react';
import { AlertCircle, Loader } from 'lucide-react';

interface LoginPageProps {
  onLoginSuccess?: (user: any) => void;
}

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [googleScriptLoaded, setGoogleScriptLoaded] = useState(false);

  // Load Google Sign-In script
  useEffect(() => {
    if (!window.google) {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        setGoogleScriptLoaded(true);
        initializeGoogleSignIn();
      };
      document.body.appendChild(script);
    } else {
      setGoogleScriptLoaded(true);
      initializeGoogleSignIn();
    }
  }, []);

  const initializeGoogleSignIn = () => {
    if (window.google && GOOGLE_CLIENT_ID) {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleSignIn,
      });
      window.google.accounts.id.renderButton(
        document.getElementById('google-signin-button'),
        {
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
        }
      );
    }
  };

  const handleGoogleSignIn = async (response: any) => {
    try {
      setLoading(true);
      setError(null);

      const token = response.credential;

      // Send token to backend for verification and session creation
      const res = await fetch('/api/auth/google', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'Auth failed' }));
        throw new Error(errorData.detail || 'Authentication failed');
      }

      const userData = await res.json();

      // Store user info and token
      localStorage.setItem('auth_token', userData.access_token);
      localStorage.setItem('user_info', JSON.stringify(userData.user));

      // Redirect to dashboard
      if (onLoginSuccess) {
        onLoginSuccess(userData.user);
      } else {
        window.location.href = '/';
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      console.error('Google Sign-In error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-[#112E51] to-[#0076D6]">
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full mx-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[#0B1F33] mb-2">Sentry</h1>
          <p className="text-sm text-[#5C5C5C]">CBP Trade Enforcement Platform</p>
        </div>

        {/* Logo/Icon */}
        <div className="text-center mb-8">
          <div className="inline-block p-4 bg-[#F7F9FC] rounded-full">
            <svg
              className="w-12 h-12 text-[#005EA2]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-900 font-medium">Authentication Error</p>
              <p className="text-xs text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Welcome Message */}
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-[#0B1F33] font-medium mb-2">Welcome, CBP Officer</p>
          <p className="text-xs text-[#5C5C5C]">
            Sign in with your CBP Google account to access the investigation workspace and risk assessment tools.
          </p>
        </div>

        {/* Google Sign-In Button */}
        <div className="mb-6">
          {googleScriptLoaded ? (
            <>
              <div id="google-signin-button" className="flex justify-center mb-4" />
              {loading && (
                <div className="flex items-center justify-center space-x-2 text-[#005EA2]">
                  <Loader className="w-4 h-4 animate-spin" />
                  <span className="text-sm font-medium">Signing in...</span>
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center space-x-2 text-slate-500">
              <Loader className="w-4 h-4 animate-spin" />
              <span className="text-sm">Loading sign-in...</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center pt-4 border-t border-slate-200">
          <p className="text-[9px] text-[#5C5C5C] font-mono">
            U.S. Customs and Border Protection
            <br />
            Trade Enforcement & Compliance System
          </p>
        </div>
      </div>
    </div>
  );
}

// Extend window to include google object
declare global {
  interface Window {
    google?: any;
  }
}
