"use client";

import { useState } from "react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [html, setHtml] = useState(""); // Changed from html to summary
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleClone = async () => {
    setLoading(true);
    setError("");
    setHtml("");
    try {
      const res = await fetch("http://localhost:8000/scrape-and-analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to fetch summary.");
      }

      const data = await res.json();
      setHtml(data.html); // Changed to data.summary
    } catch (err) {
      console.error(err);
      const errorMessage =
        err instanceof Error
          ? err.message
          : typeof err === "string"
            ? err
            : "Unknown error";
      setError(`Something went wrong: ${errorMessage}`);
    }
    setLoading(false);
  };

  const downloadHtml = () => {
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "cloned-site.html";
    link.click();
  };

  return (
    <main className="flex flex-col gap-6 items-center p-8 min-h-screen">
      <h1 className="text-2xl font-bold">Orchids Website Analyzer</h1> {/* Updated title */}
      <input
        className="border px-4 py-2 rounded w-80"
        placeholder="Enter website URL"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />
      <button
        onClick={handleClone}
        disabled={loading || !url}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
      >
        {loading ? "Analyzing..." : "Analyze Website"} {/* Updated button text */}
      </button>

      {error && <p className="text-red-500">{error}</p>}

      <iframe
        srcDoc={html}
        className="w-full h-[600px] border rounded"
        title="Cloned Website Preview"
      />
    </main>
  );


}