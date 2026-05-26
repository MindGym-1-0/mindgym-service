// src/app/(main)/coach/interviews/page.tsx

"use client";

import { useRouter } from "next/navigation";

export default function InterviewsPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold">
            Interviews
          </h1>

          <p className="text-gray-500 mt-1">
            Track and prepare for every upcoming interview
          </p>
        </div>

        <button
          onClick={() =>
            router.push("/coach/interviews/add")
          }
          className="bg-[#0D7C66] text-white px-5 py-3 rounded-xl"
        >
          + Add interview
        </button>
      </div>

      <div className="space-y-5">
        {[1, 2].map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-2xl p-6 shadow-sm flex items-center justify-between"
          >
            <div>
              <h2 className="font-semibold text-lg">
                Google — Product Designer
              </h2>

              <p className="text-gray-500">
                Tomorrow • 10:00 AM video call
              </p>
            </div>

            <button className="bg-[#0D7C66] text-white px-4 py-2 rounded-lg">
              Start prep →
            </button>
          </div>
        ))}
      </div>

      <h2 className="mt-12 text-xl font-semibold mb-4">
        Past interviews
      </h2>

      <div className="bg-white rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between py-4 border-b">
          <div>
            <h3 className="font-medium">
              Google — Product Designer
            </h3>

            <p className="text-gray-500 text-sm">
              3 weeks ago • No offer received
            </p>
          </div>

          <button className="border px-4 py-2 rounded-lg">
            Recovery session →
          </button>
        </div>
      </div>
    </div>
  );
}