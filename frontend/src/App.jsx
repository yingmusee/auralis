import { useEffect, useRef, useState } from 'react';
import { api } from './api';

function normalizeRows(payload) { return Array.isArray(payload) ? payload : [payload]; }

export default function App() {
  const [rows, setRows] = useState([]);
  const [files, setFiles] = useState([]);
  const [query, setQuery] = useState('');
  const [activeQuery, setActiveQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const audioInputRef = useRef(null);

  const load = async () => {
    try { setRows(normalizeRows(await api.list())); setError(''); }
    catch (cause) { setError(`Could not load transcriptions: ${cause.message}`); }
  };
  useEffect(() => { load(); }, []);

  const addFiles = (fileList) => {
    const incoming = Array.from(fileList).filter((file) => !file.type || file.type.startsWith('audio/'));
    if (incoming.length) setFiles(incoming);
    return incoming;
  };

  const clearFiles = () => {
    setFiles([]);
    if (audioInputRef.current) audioInputRef.current.value = '';
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    const incoming = addFiles(event.dataTransfer.files);
    // Dropping only updates our own React state, not the <input>'s real DOM `.files` --
    // so without this, the browser's native "No file chosen" text next to the input never
    // updates on drop, even though our own `.hint` paragraph does (it just reads `files`).
    if (audioInputRef.current && incoming.length && typeof DataTransfer !== 'undefined') {
      const dataTransfer = new DataTransfer();
      incoming.forEach((file) => dataTransfer.items.add(file));
      audioInputRef.current.files = dataTransfer.files;
    }
  };

  const upload = async (event) => {
    event.preventDefault();
    if (!files.length) return setError('Choose at least one audio file first.');
    setBusy(true); setError(''); setProgress(0);
    try {
      // /transcribe reports each file's outcome independently (HTTP status alone can't
      // tell us: 200 and 207 both mean "the request was handled", not "every file succeeded").
      const results = await api.transcribe(files, setProgress);
      const failed = results.filter((result) => result.status === 'error');
      if (failed.length) {
        setError(`Failed to transcribe ${failed.map((result) => result.filename).join(', ')}.`);
      }
      setFiles([]);
      if (audioInputRef.current) audioInputRef.current.value = '';
      await load();
    }
    catch (cause) { setError(`Transcription failed: ${cause.message}`); }
    finally { setBusy(false); setProgress(null); }
  };

  const search = async (event) => {
    event.preventDefault();
    const trimmed = query.trim();
    try { setRows(normalizeRows(trimmed ? await api.search(trimmed) : await api.list())); setActiveQuery(trimmed); setError(''); }
    catch (cause) { setError(`Search failed: ${cause.message}`); }
  };

  return <main>
    <header><p className="eyebrow">Auralis</p><h1>Audio, turned into answers.</h1><p>Upload recordings, let the service transcribe them, then find what matters.</p></header>
    <section className="panel"><h2>Transcribe audio</h2><form onSubmit={upload}>
      <div
        className={`dropzone${isDragging ? ' dragging' : ''}`}
        data-testid="dropzone"
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setIsDragging(false); }}
        onDrop={handleDrop}
      >
        <label htmlFor="audio">Audio files</label><input ref={audioInputRef} id="audio" type="file" accept="audio/*" multiple onChange={(e) => addFiles(e.target.files)} />
        <p className="hint">{files.length ? `${files.length} file${files.length === 1 ? '' : 's'} selected` : 'Drag and drop audio files here, or choose files.'}{files.length ? <button type="button" className="linkButton" onClick={clearFiles}>Clear</button> : null}</p>
      </div>
      <button disabled={busy}>{busy ? (progress != null && progress < 100 ? `Uploading… ${progress}%` : 'Transcribing…') : 'Upload and transcribe'}</button>
      {/* aria-valuenow is only included while progress is a known percentage. api.js sets
          progress back to null once the upload itself finishes (loaded === total) since
          the subsequent server-side transcription step has no percentage to report --
          always passing aria-valuenow={progress ?? 0} would make a screen reader announce
          a stale "100%" for however long transcription takes, instead of "unknown". */}
      {busy && <div className={`progress${progress != null && progress < 100 ? '' : ' indeterminate'}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} {...(progress != null ? { 'aria-valuenow': progress } : {})}>
        <div className="progressBar" style={progress != null && progress < 100 ? { width: `${progress}%` } : undefined} />
      </div>}
    </form></section>
    <section className="panel"><div className="tableHeading"><div><h2>Transcriptions</h2><p>{rows.length} result{rows.length === 1 ? '' : 's'}</p></div><form className="search" onSubmit={search}><label className="srOnly" htmlFor="search">Search by filename</label><input id="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search filenames" /><button>Search</button></form></div>
      {error && <p role="alert" className="error">{error}</p>}
      {/* "No transcriptions yet." only applies when the DB is genuinely empty. Reusing
          it after a search that legitimately matches nothing would falsely tell the user
          the whole system has no data, instead of "your search had no results" -- so the
          empty state branches on the last *submitted* query (activeQuery), not the live
          `query` input. Branching on `query` directly made clearing the search box (without
          re-submitting) relabel the still-stale search results as "No transcriptions yet.",
          which is wrong whenever the database actually has data. */}
      <div className="tableWrap"><table><thead><tr><th>Filename</th><th>Transcript</th><th>Created</th></tr></thead><tbody>{rows.length ? rows.map((row) => <tr key={row.id ?? row.filename}><td>{row.original_filename ?? row.filename}</td><td>{row.transcript}</td><td>{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td></tr>) : <tr><td colSpan="3" className="empty">{activeQuery ? `No results for "${activeQuery}".` : 'No transcriptions yet.'}</td></tr>}</tbody></table></div>
    </section>
  </main>;
}
