// src/app/(main)/sessions/page.tsx

"use client";

import Link from "next/link";

const sessions = [
  {
    title: "Calm Reset",
    subtitle: "5 min • Breathing reset",
    emoji: "🫁",
  },
  {
    title: "Confidence Builder",
    subtitle: "10 min • Maya guided",
    emoji: "💪",
  },
  {
    title: "Think Clearly Under Pressure",
    subtitle: "10 min • Focus + calm",
    emoji: "🧠",
  },
];

export default function SessionsPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <p className="text-sm text-gray-500">
            Overview {" > "} Daily Dashboard
          </p>

          <h1 className="text-4xl font-semibold mt-2">
            Sessions
          </h1>
        </div>

        <Link
          href="/sessions/setup/emotions"
          className="bg-[#0C6B58] text-white px-5 py-3 rounded-xl"
        >
          Start session →
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {sessions.map((session) => (
          <div
            key={session.title}
            className="bg-white rounded-3xl p-6 border border-gray-200"
          >
            <div className="text-5xl mb-4">
              {session.emoji}
            </div>

            <h2 className="text-xl font-semibold">
              {session.title}
            </h2>

            <p className="text-gray-500 mt-2">
              {session.subtitle}
            </p>

            <button className="mt-6 bg-[#0C6B58] text-white px-4 py-2 rounded-lg">
              Start
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}