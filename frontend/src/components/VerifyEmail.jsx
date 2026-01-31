import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { api } from '../utils/api';

export const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('loading'); // loading | success | error
  const [message, setMessage] = useState('');

  useEffect(() => {
    const username = searchParams.get('username');
    const token = searchParams.get('token');

    if (!username || !token) {
      setStatus('error');
      setMessage('Missing verification details.');
      return;
    }

    api.verifyEmail(username, token)
      .then((data) => {
        setStatus('success');
        setMessage(data.message || 'Email verified successfully.');
      })
      .catch((err) => {
        setStatus('error');
        setMessage(err.message || 'Verification failed.');
      });
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">Verify Email</h1>
        {status === 'loading' && (
          <p className="text-gray-600">Verifying your email...</p>
        )}
        {status !== 'loading' && (
          <p className={status === 'success' ? 'text-green-600' : 'text-red-600'}>
            {message}
          </p>
        )}
        <Link
          to="/"
          className="mt-6 inline-block text-blue-600 hover:text-blue-800 text-sm"
        >
          Back to login
        </Link>
      </div>
    </div>
  );
};
