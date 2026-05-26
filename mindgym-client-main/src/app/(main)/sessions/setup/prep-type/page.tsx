// src/app/(main)/sessions/setup/prep-type/page.tsx

"use client";

import Link from "next/link";

const types = [
  "Interview tomorrow",
  "Recruiter call",
  "Rejection recovery",
  "Networking",
  "Salary negotiation",
];

export default function PrepTypePage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <p className="text-[#0C6B58] mb-8">
        Session setup • Step 2 of 4
      </p>

      <div className="text-center">
        <h1 className="text-4xl font-semibold">
          What are you preparing for?
        </h1>

        <div className="flex flex-wrap justify-center gap-4 mt-8">
          {types.map((type) => (
            <button
              key={type}
              className="px-5 py-3 rounded-full border bg-white hover:bg-[#DDF4EE]"
            >
              {type}
            </button>
          ))}
        </div>

        <div className="flex justify-center gap-4 mt-10">
          <Link
            href="/sessions/setup/emotions"
            className="px-5 py-3 rounded-xl border"
          >
            ← Back
          </Link>

          <Link
            href="/sessions/setup/feelings"
            className="bg-[#0C6B58] text-white px-5 py-3 rounded-xl"
          >
            Continue →
          </Link>
        </div>
      </div>
    </div>
  );
}