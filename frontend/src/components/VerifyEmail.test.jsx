import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { VerifyEmail } from './VerifyEmail';

vi.mock('../utils/api', () => ({
  api: {
    verifyEmail: vi.fn(() => Promise.resolve({ message: 'Verified' }))
  }
}));

const renderWithRoute = (route) => {
  render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/verify-email" element={<VerifyEmail />} />
      </Routes>
    </MemoryRouter>
  );
};

test('verifies email when params are present', async () => {
  renderWithRoute('/verify-email?username=alice&token=abc');
  expect(screen.getByText(/verifying/i)).toBeInTheDocument();

  await waitFor(() => {
    expect(screen.getByText(/verified/i)).toBeInTheDocument();
  });
});

test('shows error when params are missing', async () => {
  renderWithRoute('/verify-email');
  await waitFor(() => {
    expect(screen.getByText(/missing verification/i)).toBeInTheDocument();
  });
});
