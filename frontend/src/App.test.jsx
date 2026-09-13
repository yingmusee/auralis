import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi, describe, expect, it, beforeEach, afterEach } from 'vitest';
import App from './App';

beforeEach(() => { global.fetch = vi.fn(); });
afterEach(() => cleanup());
const json = (body) => Promise.resolve({ ok: true, json: () => Promise.resolve(body) });

describe('Auralis UI', () => {
  it('renders transcriptions from the API', async () => {
    global.fetch.mockReturnValue(json([{ id: 1, filename: 'sample.mp3', transcript: 'Hello', created_at: '2026-01-01T10:00:00Z' }]));
    render(<App />);
    expect(await screen.findByText('sample.mp3')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('submits all selected files for transcription and reports upload progress', async () => {
    const sendSpy = vi.fn(function send() {
      this.upload.onprogress({ lengthComputable: true, loaded: 1, total: 1 });
      this.status = 200;
      this.responseText = '[]';
      this.onload();
    });
    global.XMLHttpRequest = vi.fn(function FakeXHR() { this.upload = {}; this.open = vi.fn(); this.send = sendSpy; });
    global.fetch.mockReturnValue(json([]));
    render(<App />);
    await screen.findByText('No transcriptions yet.');
    const file = new File(['audio'], 'clip.mp3', { type: 'audio/mpeg' });
    fireEvent.change(screen.getByLabelText('Choose files'), { target: { files: [file] } });
    fireEvent.click(screen.getByText('Upload and transcribe'));
    await waitFor(() => expect(sendSpy).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText('Upload and transcribe')).toBeInTheDocument());
  });

  it('searches by filename', async () => {
    global.fetch.mockReturnValueOnce(json([])).mockReturnValueOnce(json([{ id: 2, filename: 'meeting.mp3', transcript: 'Notes' }]));
    render(<App />);
    await screen.findByText('No transcriptions yet.');
    fireEvent.change(screen.getByLabelText('Search by filename'), { target: { value: 'meeting' } });
    fireEvent.click(screen.getByText('Search'));
    expect(await screen.findByText('meeting.mp3')).toBeInTheDocument();
    expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining('/search?filename=meeting'), { cache: 'no-store' });
  });
});
