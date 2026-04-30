'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { setTokens } from '@/lib/api';

declare global {
  interface Window {
    google: any;
  }
}

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? '';

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState('');

  const submitIdToken = async (idToken: string) => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/auth/login/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken }),
      });

      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || 'Login failed');
        return;
      }

      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      router.push('/dashboard');
    } catch (e) {
      setError('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
  };

  useEffect(() => {
    // OAuth redirect 후 URL 해시에서 id_token 추출 (다른 계정 로그인 flow)
    const hash = window.location.hash.slice(1);
    if (hash) {
      const params = new URLSearchParams(hash);
      const idToken = params.get('id_token');
      if (idToken) {
        window.history.replaceState({}, '', '/login');
        submitIdToken(idToken);
        return;
      }
    }

    if (!CLIENT_ID) {
      setError('Google Client ID가 설정되지 않았습니다. frontend/.env.local을 확인하세요.');
      return;
    }

    const initGoogle = () => {
      if (!window.google) return;
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: (response: any) => submitIdToken(response.credential),
        auto_select: false,
        cancel_on_tap_outside: false,
      });
      window.google.accounts.id.renderButton(
        document.getElementById('google-login-btn'),
        { theme: 'outline', size: 'large', width: 300, type: 'standard' }
      );
      window.google.accounts.id.disableAutoSelect();
    };

    if (window.google) {
      initGoogle();
    } else {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.onload = initGoogle;
      document.body.appendChild(script);
    }
  }, []);

  // redirect_uri를 현재 /login 페이지로 설정 → URL 해시로 id_token 수신
  const handleSelectAccount = () => {
    if (!CLIENT_ID) {
      setError('Google Client ID가 설정되지 않았습니다.');
      return;
    }
    const params = new URLSearchParams({
      client_id: CLIENT_ID,
      redirect_uri: `${window.location.origin}/login`,
      response_type: 'id_token',
      scope: 'openid email profile',
      prompt: 'select_account',
      nonce: Math.random().toString(36).slice(2),
    });
    window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-lg p-10 w-full max-w-sm flex flex-col items-center gap-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">ParaWorks</h1>
          <p className="text-sm text-gray-500 mt-1">Intelligent Workplace Collaboration</p>
        </div>
        {error && (
          <p className="text-sm text-red-500 text-center">{error}</p>
        )}
        <div id="google-login-btn" />
        <button
          onClick={handleSelectAccount}
          className="text-sm text-blue-600 hover:underline"
        >
          다른 계정으로 로그인
        </button>
        <p className="text-xs text-gray-400 text-center">
          회사 계정으로 로그인하세요
        </p>
      </div>
    </div>
  );
}
