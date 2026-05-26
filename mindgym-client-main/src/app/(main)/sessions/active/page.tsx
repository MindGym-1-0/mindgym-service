// src/app/(main)/sessions/active/page.tsx

"use client";

import Link from "next/link";

export default function ActiveSessionPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <div className="bg-white rounded-3xl p-6 border mb-8">
        <h1 className="text-2xl font-semibold">
          Maya is guiding your session
        </h1>

        <p className="text-gray-500 mt-2">
          Phase 1 of 5 • 5 min session
        </p>
      </div>

      <div className="grid grid-cols-[2fr_1fr] gap-6">
        <div className="rounded-3xl bg-gradient-to-br from-[#032F2B] to-[#0C6B58] p-10 text-white min-h-[500px] flex flex-col items-center justify-center">
          <div className="text-7xl mb-6">
            🫁
          </div>

          <h2 className="text-4xl font-semibold">
            Breathe in slowly...
          </h2>

          <p className="mt-4 text-center max-w-lg text-gray-200">
            Let your shoulders drop. You don’t need to
            have everything figured out right now.
          </p>

          <div className="flex gap-4 mt-10">
            <button className="bg-white text-black px-5 py-3 rounded-xl">
              Pause
            </button>

            <Link
              href="/sessions/feedback"
              className="bg-[#1A8A74] px-5 py-3 rounded-xl"
            >
              End session →
            </Link>
          </div>
        </div>

        <div className="space-y-4">
          {[
            "Phase 1 • Active",
            "Phase 2 • Ground",
            "Phase 3 • Rehearse",
            "Phase 4 • Anchor",
            "Phase 5 • Close",
          ].map((phase) => (
            <div
              key={phase}
              className="bg-white rounded-2xl p-5 border"
            >
              {phase}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}