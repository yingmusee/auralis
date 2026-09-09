import { useEffect, useRef, useState } from 'react';
import { api } from './api';

function normalizeRows(payload) { return Array.isArray(payload) ? payload : [payload]; }

export default function App() {
  const [rows, setRows] = useState([]);
  const [files, setFiles] = useState([]);
  const [query, setQuery] = useState('');
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
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    addFiles(event.dataTransfer.files);
  };

  const upload = async (event) => {
    event.preventDefault();
    if (!files.length) return setError('Choose at least one audio file first.');
    setBusy(true); setError(''); setProgress(0);
    try {
      await api.transcribe(files, setProgress);
      setFiles([]);
      if (audioInputRef.current) audioInputRef.current.value = '';
      await load();
    }
    catch (cause) { setError(`Transcription failed: ${cause.message}`); }
    finally { setBusy(false); setProgress(null); }
  };

  const search = async (event) => {
    event.preventDefault();
    try { setRows(normalizeRows(query.trim() ? await api.search(query.trim()) : await api.list())); setError(''); }
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
        <p className="hint">{files.length ? `${files.length} file${files.length === 1 ? '' : 's'} selected` : 'Drag and drop audio files here, or choose files.'}</p>
      </div>
      <button disabled={busy}>{busy ? (progress != null && progress < 100 ? `Uploading… ${progress}%` : 'Transcribing…') : 'Upload and transcribe'}</button>
      {busy && <div className={`progress${progress != null && progress < 100 ? '' : ' indeterminate'}`} role="progressbar" aria-valuenow={progress ?? 0} aria-valuemin={0} aria-valuemax={100}>
        <div className="progressBar" style={progress != null && progress < 100 ? { width: `${progress}%` } : undefined} />
      </div>}
    </form></section>
    <section className="panel"><div className="tableHeading"><div><h2>Transcriptions</h2><p>{rows.length} result{rows.length === 1 ? '' : 's'}</p></div><form className="search" onSubmit={search}><label className="srOnly" htmlFor="search">Search by filename</label><input id="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search filenames" /><button>Search</button></form></div>
      {error && <p role="alert" className="error">{error}</p>}
      <div className="tableWrap"><table><thead><tr><th>Filename</th><th>Transcript</th><th>Created</th></tr></thead><tbody>{rows.length ? rows.map((row) => <tr key={row.id ?? row.filename}><td>{row.original_filename ?? row.filename}</td><td>{row.transcript}</td><td>{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td></tr>) : <tr><td colSpan="3" className="empty">No transcriptions yet.</td></tr>}</tbody></table></div>
    </section>
  </main>;
}
