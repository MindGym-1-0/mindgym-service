// src/app/(main)/sessions/setup/time/page.tsx

"use client";

import Link from "next/link";

const times = [
  "5 min",
  "10 min",
  "15 min",
];

export default function TimePage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <p className="text-[#0C6B58] mb-8">
        Session setup • Step 3b of 4
      </p>

      <div className="text-center">
        <h1 className="text-4xl font-semibold">
          How much time do you have?
        </h1>

        <div className="flex justify-center gap-4 mt-8">
          {times.map((time) => (
            <button
              key={time}
              className="px-6 py-4 rounded-2xl border bg-white hover:bg-[#DDF4EE]"
            >
              {time}
            </button>
          ))}
        </div>

        <div className="flex justify-center gap-4 mt-10">
          <Link
            href="/sessions/setup/feelings"
            className="px-5 py-3 rounded-xl border"
          >
            ← Back
          </Link>

          <Link
            href="/sessions/setup/summary"
            className="bg-[#0C6B58] text-white px-5 py-3 rounded-xl"
          >
            Continue →
          </Link>
        </div>
      </div>
    </div>
  );
}