'use client';

import { useState } from 'react';

export default function Home() {
  const [url, setUrl] = useState('');
  const [clonedHTML, setClonedHTML] = useState('');
  const [loading, setLoading] = useState(false);

  const handleClone = async () => {
    setLoading(true);
    const res = await fetch('http://localhost:8000/api/clone', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    const data = await res.json();
    setClonedHTML(data.cloned_html || '');
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-neutral-900 p-6 flex flex-col items-center text-white">
      <div className="max-w-3xl w-full bg-neutral-800 shadow-lg rounded-xl p-8">
        <h1 className="text-3xl font-extrabold text-center text-blue-700 mb-6">
          🌸 Orchids Website Cloner
        </h1>

        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <input
            type="text"
            placeholder="Enter a public website URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-grow border border-gray-600 rounded-lg px-4 py-2 shadow-sm bg-neutral-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            onClick={handleClone}
            className="bg-blue-600 hover:bg-blue-700 transition text-white px-6 py-2 rounded-lg shadow font-semibold"
          >
            {loading ? 'Cloning...' : 'Clone Website'}
          </button>
        </div>

        {loading && (
          <div className="flex justify-center mt-4 text-blue-600">
            <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
            Cloning in progress...
          </div>
        )}

        {clonedHTML && (
          <div className="mt-8 border border-gray-300 rounded-md overflow-hidden">
            <iframe
              className="w-full h-[1000px]"
              srcDoc={clonedHTML}
              sandbox=""
            />
          </div>
        )}
      </div>
    </main>
  );
}