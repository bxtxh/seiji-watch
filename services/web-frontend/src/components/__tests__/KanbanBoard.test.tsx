import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import KanbanBoard from '../KanbanBoard';
import { useRouter } from 'next/router';

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

// Mock intersection observer
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
});
window.IntersectionObserver = mockIntersectionObserver;

// Mock fetch
global.fetch = jest.fn();

describe('KanbanBoard', () => {
  const mockPush = jest.fn();
  const mockPrefetch = jest.fn();

  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      prefetch: mockPrefetch,
    });
    jest.clearAllMocks();
  });

  it('renders loading skeleton initially', () => {
    render(<KanbanBoard />);
    
    // Should show loading state
    expect(screen.getByText('読み込み中...')).toBeInTheDocument();
  });

  it('renders kanban board with issues', async () => {
    const mockKanbanData = {
      success: true,
      data: {
        stages: {
          backlog: [],
          in_progress: [
            {
              id: 'rec1',
              title: 'Test Issue 1',
              stage: 'in_progress',
              schedule: { from: '2025-07-01', to: '2025-07-28' },
              tags: ['tag1'],
              related_bills: [],
              updated_at: '2025-07-12T10:00:00Z',
            },
          ],
          in_review: [],
          completed: [],
        },
      },
      metadata: {
        total_issues: 1,
        last_updated: '2025-07-12T10:00:00Z',
        date_range: { from: '2025-07-01', to: '2025-07-28' },
      },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockKanbanData,
    });

    render(<KanbanBoard />);

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('1件のイシューを表示中')).toBeInTheDocument();
    });

    // Check if stages are rendered
    expect(screen.getByText('審議中')).toBeInTheDocument();
    expect(screen.getByText('採決待ち')).toBeInTheDocument();
    expect(screen.getByText('成立')).toBeInTheDocument();

    // Check if issue is rendered
    expect(screen.getByText('Test Issue 1')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

    render(<KanbanBoard />);

    await waitFor(() => {
      expect(screen.getByText('エラーが発生しました')).toBeInTheDocument();
    });

    // Should show retry button
    expect(screen.getByText('再読み込み')).toBeInTheDocument();
  });

  it('handles empty stages correctly', async () => {
    const mockEmptyData = {
      success: true,
      data: {
        stages: {
          backlog: [],
          in_progress: [],
          in_review: [],
          completed: [],
        },
      },
      metadata: {
        total_issues: 0,
        last_updated: '2025-07-12T10:00:00Z',
        date_range: { from: '2025-07-01', to: '2025-07-28' },
      },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockEmptyData,
    });

    render(<KanbanBoard />);

    await waitFor(() => {
      expect(screen.getByText('0件のイシューを表示中')).toBeInTheDocument();
    });

    // Should show empty state for 成立 stage
    expect(screen.getByText('現在成立のイシューはありません')).toBeInTheDocument();
  });

  it('navigates to issue detail on card click', async () => {
    const mockKanbanData = {
      success: true,
      data: {
        stages: {
          backlog: [],
          in_progress: [
            {
              id: 'rec123',
              title: 'Clickable Issue',
              stage: 'in_progress',
              schedule: { from: '2025-07-01', to: '2025-07-28' },
              tags: [],
              related_bills: [],
              updated_at: '2025-07-12T10:00:00Z',
            },
          ],
          in_review: [],
          completed: [],
        },
      },
      metadata: {
        total_issues: 1,
        last_updated: '2025-07-12T10:00:00Z',
        date_range: { from: '2025-07-01', to: '2025-07-28' },
      },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockKanbanData,
    });

    render(<KanbanBoard />);

    await waitFor(() => {
      expect(screen.getByText('Clickable Issue')).toBeInTheDocument();
    });

    // Click on the issue card
    const issueCard = screen.getByText('Clickable Issue').closest('article');
    issueCard?.click();

    // Should navigate to issue detail page
    expect(mockPush).toHaveBeenCalledWith('/issues/rec123');
  });
});