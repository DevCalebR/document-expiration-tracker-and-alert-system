import React, { useState } from 'react';
import { UserPlus } from 'lucide-react';
import { api } from '../utils/api';

export const Register = ({ onBackToLogin }) => {
  const [form, setForm] = useState({
    username: '',
    email: '',
    full_name: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await api.register(form);
      setSuccess('Account created! Check your email to verify your account.');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <UserPlus className="mx-auto text-blue-600 mb-4" size={64} />
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Create Account</h1>
          <p className="text-gray-600">Register to use DocExpire</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            name="username"
            placeholder="Username"
            value={form.username}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 border rounded-lg"
          />
          <input
            name="email"
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 border rounded-lg"
          />
          <input
            name="full_name"
            placeholder="Full Name"
            value={form.full_name}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 border rounded-lg"
          />
          <input
            name="password"
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 border rounded-lg"
          />

          {error && <div className="bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm">{error}</div>}
          {success && <div className="bg-green-50 text-green-600 px-4 py-2 rounded-lg text-sm">{success}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <button
          onClick={onBackToLogin}
          className="mt-6 text-blue-600 hover:text-blue-800 text-sm"
        >
          ← Back to login
        </button>
      </div>
    </div>
  );
};

