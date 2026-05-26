// src/app/(main)/sessions/setup/summary/page.tsx

"use client";

import Link from "next/link";

export default function SummaryPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <p className="text-[#0C6B58] mb-8">
        Session setup • Step 4 of 4
      </p>

      <div className="max-w-3xl mx-auto text-center">
        <h1 className="text-5xl font-semibold">
          Ready when you are
        </h1>

        <div className="bg-white rounded-3xl p-8 mt-8 border text-left">
          <p className="text-gray-500 mb-4">
            Your session
          </p>

          <p className="text-2xl leading-relaxed">
            You’re preparing for tomorrow’s final interview
            and want to feel grounded and clear.
          </p>

          <div className="flex gap-3 mt-6">
            <div className="bg-yellow-100 px-3 py-1 rounded-full text-sm">
              Interview tomorrow
            </div>

            <div className="bg-green-100 px-3 py-1 rounded-full text-sm">
              Grounded
            </div>

            <div className="bg-blue-100 px-3 py-1 rounded-full text-sm">
              5 mins
            </div>
          </div>
        </div>

        <div className="flex justify-center gap-4 mt-10">
          <Link
            href="/sessions/setup/time"
            className="px-5 py-3 rounded-xl border"
          >
            ← Change something
          </Link>

          <Link
            href="/sessions/active"
            className="bg-[#0C6B58] text-white px-5 py-3 rounded-xl"
          >
            Begin session →
          </Link>
        </div>
      </div>
    </div>
  );
}