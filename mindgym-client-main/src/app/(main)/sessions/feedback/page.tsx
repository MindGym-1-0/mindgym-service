// src/app/(main)/sessions/feedback/page.tsx

"use client";

import Link from "next/link";

export default function FeedbackPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <div className="max-w-3xl mx-auto text-center">
        <h1 className="text-5xl font-semibold">
          How do you feel now?
        </h1>

        <p className="text-gray-500 mt-3">
          Even a small shift is progress.
        </p>

        <div className="bg-white rounded-3xl p-8 mt-10 border">
          <div className="flex justify-between text-sm">
            <span>Not ready</span>
            <span>Fully ready</span>
          </div>

          <div className="w-full h-3 bg-gray-200 rounded-full mt-4">
            <div className="w-[80%] h-full bg-[#0C6B58] rounded-full" />
          </div>

          <div className="mt-8 flex justify-center gap-4 flex-wrap">
            {[
              "More focused",
              "Less anxious",
              "Confident",
              "Grounded",
            ].map((tag) => (
              <div
                key={tag}
                className="px-4 py-2 rounded-full bg-[#DDF4EE]"
              >
                {tag}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 border mt-8 text-left">
          <p>
            “You went from 4 → 8. That shift is real.”
          </p>
        </div>

        <div className="flex justify-center gap-4 mt-10">
          <Link
            href="/dashboard"
            className="bg-[#0C6B58] text-white px-5 py-3 rounded-xl"
          >
            ← Back to dashboard
          </Link>

          <button className="border px-5 py-3 rounded-xl bg-white">
            Save session
          </button>
        </div>
      </div>
    </div>
  );
}