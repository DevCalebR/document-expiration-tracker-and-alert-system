import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Register } from './Register';
import { api } from '../utils/api';

vi.mock('../utils/api', () => ({
  api: {
    register: vi.fn()
  }
}));

const fillForm = async () => {
  const user = userEvent.setup();
  await user.type(screen.getByPlaceholderText(/username/i), 'alice');
  await user.type(screen.getByPlaceholderText(/email/i), 'alice@example.com');
  await user.type(screen.getByPlaceholderText(/full name/i), 'Alice Example');
  await user.type(screen.getByPlaceholderText(/password/i), 'password123');
  await user.click(screen.getByRole('button', { name: /register/i }));
};

test('shows manual verification link when smtp is unavailable', async () => {
  api.register.mockResolvedValue({
    message: 'User registered. SMTP is not configured, so use the verification link below.',
    verification_url: 'http://localhost:5173/verify-email?username=alice&token=abc123'
  });

  render(<Register onBackToLogin={() => {}} />);
  await act(async () => {
    await fillForm();
  });

  await waitFor(() => {
    expect(screen.getByText(/local verification link/i)).toBeInTheDocument();
  });

  expect(screen.getByRole('link')).toHaveAttribute(
    'href',
    'http://localhost:5173/verify-email?username=alice&token=abc123'
  );
});

test('surfaces the backend success message when email delivery is configured', async () => {
  api.register.mockResolvedValue({
    message: 'User registered. Verification email sent.'
  });

  render(<Register onBackToLogin={() => {}} />);
  await act(async () => {
    await fillForm();
  });

  await waitFor(() => {
    expect(screen.getByText(/verification email sent/i)).toBeInTheDocument();
  });

  expect(screen.queryByText(/local verification link/i)).not.toBeInTheDocument();
});
