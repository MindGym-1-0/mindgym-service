// src/app/(main)/sessions/setup/emotions/page.tsx

"use client";

import Link from "next/link";

const emotions = [
  "😟 Overwhelmed",
  "😕 Discouraged",
  "😴 Exhausted",
  "😶 Unsure",
  "😬 Anxious but hopeful",
];

export default function EmotionsPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <p className="text-[#0C6B58] mb-8">
        Session setup • Step 1 of 4
      </p>

      <div className="max-w-4xl mx-auto text-center">
        <h1 className="text-4xl font-semibold">
          How are you feeling right now?
        </h1>

        <p className="text-gray-500 mt-3">
          Your answer shapes the session Maya prepares for you.
        </p>

        <div className="flex flex-wrap justify-center gap-4 mt-8">
          {emotions.map((emotion) => (
            <button
              key={emotion}
              className="px-5 py-3 rounded-full border bg-white hover:bg-[#DDF4EE]"
            >
              {emotion}
            </button>
          ))}
        </div>

        <div className="bg-white rounded-3xl p-6 mt-12 border">
          <input
            placeholder="Speak or type your answer..."
            className="w-full border rounded-xl px-4 py-4"
          />
        </div>

        <div className="flex justify-center gap-4 mt-8">
          <button className="px-5 py-3 rounded-xl border">
            ← Back
          </button>

          <Link
            href="/sessions/setup/prep-type"
            className="bg-[#0C6B58] text-white px-5 py-3 rounded-xl"
          >
            Continue →
          </Link>
        </div>
      </div>
    </div>
  );
}