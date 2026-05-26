// src/app/(main)/sessions/setup/feelings/page.tsx

"use client";

import Link from "next/link";

const feelings = [
  "Calm",
  "Grounded",
  "Confident",
  "Focused",
];

export default function FeelingsPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <p className="text-[#0C6B58] mb-8">
        Session setup • Step 3 of 4
      </p>

      <div className="text-center">
        <h1 className="text-4xl font-semibold">
          How would you like to feel?
        </h1>

        <div className="flex justify-center gap-4 mt-8 flex-wrap">
          {feelings.map((item) => (
            <button
              key={item}
              className="px-5 py-3 rounded-full border bg-white hover:bg-[#DDF4EE]"
            >
              {item}
            </button>
          ))}
        </div>

        <div className="flex justify-center gap-4 mt-10">
          <Link
            href="/sessions/setup/prep-type"
            className="px-5 py-3 rounded-xl border"
          >
            ← Back
          </Link>

          <Link
            href="/sessions/setup/time"
            className="bg-[#0C6B58] text-white px-5 py-3 rounded-xl"
          >
            Continue →
          </Link>
        </div>
      </div>
    </div>
  );
}