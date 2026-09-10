import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi, describe, expect, it, beforeEach, afterEach } from 'vitest';
import App from './App';

beforeEach(() => { global.fetch = vi.fn(); });
afterEach(() => cleanup());
const json = (body) => Promise.resolve({ ok: true, json: () => Promise.resolve(body) });

describe('Auralis UI', () => {
  it('renders transcriptions from the API', async () => { global.fetch.mockReturnValue(json([{ id: 1, filename: 'sample.mp3', transcript: 'Hello', created_at: '2026-01-01T10:00:00Z' }])); render(<App />); expect(await screen.findByText('sample.mp3')).toBeInTheDocument(); expect(screen.getByText('Hello')).toBeInTheDocument(); });
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
    fireEvent.change(screen.getByLabelText('Audio files'), { target: { files: [file] } });
    fireEvent.click(screen.getByText('Upload and transcribe'));
    await waitFor(() => expect(sendSpy).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText('Upload and transcribe')).toBeInTheDocument());
  });
  it('surfaces a partially-failed batch upload instead of silently succeeding', async () => {
    // /transcribe responds 207 (still a 2xx, so the XHR resolves) when some files in a
    // batch fail -- the UI must inspect each entry's status itself rather than treating
    // any 2xx as "everything succeeded".
    const sendSpy = vi.fn(function send() {
      this.status = 207;
      this.responseText = JSON.stringify([
        { status: 'ok', id: 1, filename: 'good.mp3', original_filename: 'good.mp3', transcript: 'hi', created_at: '2026-01-01T10:00:00Z' },
        { status: 'error', filename: 'bad.mp3', detail: "Failed to process 'bad.mp3': boom" },
      ]);
      this.onload();
    });
    global.XMLHttpRequest = vi.fn(function FakeXHR() { this.upload = {}; this.open = vi.fn(); this.send = sendSpy; });
    global.fetch.mockReturnValue(json([]));
    render(<App />);
    await screen.findByText('No transcriptions yet.');
    const files = [new File(['audio'], 'good.mp3', { type: 'audio/mpeg' }), new File(['audio'], 'bad.mp3', { type: 'audio/mpeg' })];
    fireEvent.change(screen.getByLabelText('Audio files'), { target: { files } });
    fireEvent.click(screen.getByText('Upload and transcribe'));
    expect(await screen.findByRole('alert')).toHaveTextContent('bad.mp3');
  });
  it('accepts audio files dropped onto the upload panel', async () => {
    global.fetch.mockReturnValue(json([]));
    render(<App />);
    await screen.findByText('No transcriptions yet.');
    const file = new File(['audio'], 'dropped.mp3', { type: 'audio/mpeg' });
    fireEvent.drop(screen.getByTestId('dropzone'), { dataTransfer: { files: [file] } });
    expect(await screen.findByText('1 file selected')).toBeInTheDocument();
  });
  it('lets the user clear a file selection instead of being stuck until they pick a replacement', async () => {
    global.fetch.mockReturnValue(json([]));
    render(<App />);
    await screen.findByText('No transcriptions yet.');
    const file = new File(['audio'], 'clip.mp3', { type: 'audio/mpeg' });
    fireEvent.change(screen.getByLabelText('Audio files'), { target: { files: [file] } });
    await screen.findByText('1 file selected');

    fireEvent.click(screen.getByText('Clear'));

    expect(await screen.findByText('Drag and drop audio files here, or choose files.')).toBeInTheDocument();
    expect(screen.queryByText('Clear')).not.toBeInTheDocument();
  });
  it('searches by filename', async () => { global.fetch.mockReturnValueOnce(json([])).mockReturnValueOnce(json([{ id: 2, filename: 'meeting.mp3', transcript: 'Notes' }])); render(<App />); await screen.findByText('No transcriptions yet.'); fireEvent.change(screen.getByLabelText('Search by filename'), { target: { value: 'meeting' } }); fireEvent.click(screen.getByText('Search')); expect(await screen.findByText('meeting.mp3')).toBeInTheDocument(); expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining('/search?filename=meeting'), undefined); });
  it('shows a query-specific empty state after a search with no results, not the generic empty-database message', async () => {
    global.fetch.mockReturnValueOnce(json([{ id: 1, filename: 'sample.mp3', transcript: 'Hello' }])).mockReturnValueOnce(json([]));
    render(<App />);
    await screen.findByText('sample.mp3');
    fireEvent.change(screen.getByLabelText('Search by filename'), { target: { value: 'zzz' } });
    fireEvent.click(screen.getByText('Search'));
    expect(await screen.findByText('No results for "zzz".')).toBeInTheDocument();
    expect(screen.queryByText('No transcriptions yet.')).not.toBeInTheDocument();
  });
  it('keeps showing the query-specific empty state after clearing the search box without resubmitting', async () => {
    // Clearing the input updates `query` on every keystroke, but the still-displayed rows
    // are whatever the last *submitted* search returned -- the empty-state message must
    // track that submitted query, not relabel stale zero-result rows as "no data at all"
    // just because the box is empty again.
    global.fetch.mockReturnValueOnce(json([{ id: 1, filename: 'sample.mp3', transcript: 'Hello' }])).mockReturnValueOnce(json([]));
    render(<App />);
    await screen.findByText('sample.mp3');
    fireEvent.change(screen.getByLabelText('Search by filename'), { target: { value: 'zzz' } });
    fireEvent.click(screen.getByText('Search'));
    await screen.findByText('No results for "zzz".');

    fireEvent.change(screen.getByLabelText('Search by filename'), { target: { value: '' } });
    expect(screen.getByText('No results for "zzz".')).toBeInTheDocument();
    expect(screen.queryByText('No transcriptions yet.')).not.toBeInTheDocument();
  });
  it('omits aria-valuenow once the upload finishes and the server is still processing, instead of announcing a stale 100%', async () => {
    let capturedXhr;
    global.XMLHttpRequest = vi.fn(function FakeXHR() { this.upload = {}; this.open = vi.fn(); this.send = vi.fn(() => { capturedXhr = this; }); });
    global.fetch.mockReturnValue(json([]));
    render(<App />);
    await screen.findByText('No transcriptions yet.');
    const file = new File(['audio'], 'clip.mp3', { type: 'audio/mpeg' });
    fireEvent.change(screen.getByLabelText('Audio files'), { target: { files: [file] } });
    fireEvent.click(screen.getByText('Upload and transcribe'));

    const bar = await screen.findByRole('progressbar');

    capturedXhr.upload.onprogress({ lengthComputable: true, loaded: 50, total: 100 });
    await waitFor(() => expect(bar).toHaveAttribute('aria-valuenow', '50'));

    // Bytes are fully sent, but we're still "busy" waiting on server-side transcription
    // with no percentage left to report -- this must read as indeterminate, not "100%".
    capturedXhr.upload.onprogress({ lengthComputable: true, loaded: 100, total: 100 });
    await waitFor(() => expect(bar).not.toHaveAttribute('aria-valuenow'));
    expect(bar.className).toContain('indeterminate');

    capturedXhr.status = 200;
    capturedXhr.responseText = '[]';
    capturedXhr.onload();
  });
});
