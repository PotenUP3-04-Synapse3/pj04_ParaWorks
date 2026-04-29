'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Script from 'next/script';
import { setTokens } from '@/lib/api';

declare global {
  interface Window {
    google: any;
  }
}

export default function LoginPage() {
  const router = useRouter();

  const handleGoogleLogin = async (response: any) => {
    try {
      const res = await fetch('/api/v1/auth/login/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential }),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || 'Login failed');
        return;
      }

      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      router.push('/dashboard');
    } catch (e) {
      alert('Login failed. Please try again.');
    }
  };

  const initGoogle = () => {
    if (!window.google) return;
    window.google.accounts.id.initialize({
      client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!,
      callback: handleGoogleLogin,
    });
    window.google.accounts.id.renderButton(
      document.getElementById('google-login-btn'),
      { theme: 'outline', size: 'large', width: 300 }
    );
  };

  useEffect(() => {
    if (window.google) {
      initGoogle();
    }
  }, []);

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={initGoogle}
      />
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-2xl shadow-lg p-10 w-full max-w-sm flex flex-col items-center gap-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900">ParaWorks</h1>
            <p className="text-sm text-gray-500 mt-1">Intelligent Workplace Collaboration</p>
          </div>
          <div id="google-login-btn" />
          <p className="text-xs text-gray-400 text-center">
            회사 계정으로 로그인하세요
          </p>
        </div>
      </div>
    </>
  );
}
