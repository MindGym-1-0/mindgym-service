// src/app/(main)/coach/interview-checkin/page.tsx

"use client";

import { useRouter } from "next/navigation";

const options = [
  {
    title: "I got the job",
    description:
      "I received an offer, or I’m expecting one very soon.",
    emoji: "🎉",
    route: "/coach/interview-checkin/got-job",
    border: "border-[#9EE5D8]",
  },
  {
    title: "Still waiting to hear back",
    description:
      "I haven’t had a response yet. The limbo is real.",
    emoji: "⏳",
    route: "/coach/interview-checkin/awaiting-response",
    border: "border-[#E9E3D5]",
  },
  {
    title: "I didn't get the role",
    description:
      "I received a rejection, or I could tell during the interview it didn’t go well.",
    emoji: "💔",
    route: "/coach/interview-checkin/rejection-recovery",
    border: "border-[#F2CACA]",
  },
];

export default function InterviewCheckinPage() {
  const router = useRouter();

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-10">
        <h1 className="text-5xl font-bold text-[#1A1A1A] mb-3">
          How did it go?
        </h1>

        <p className="text-[#6B7280] text-lg">
          Your answer helps Maya understand what you’re carrying right now.
        </p>
      </div>

      <div className="space-y-6">
        {options.map((option, index) => (
          <button
            key={index}
            onClick={() => router.push(option.route)}
            className={`w-full bg-white rounded-3xl border ${option.border} p-6 flex items-center justify-between hover:shadow-lg transition-all`}
          >
            <div className="flex items-center gap-5">
              <div className="w-14 h-14 rounded-2xl bg-[#F6F6F4] flex items-center justify-center text-2xl">
                {option.emoji}
              </div>

              <div className="text-left">
                <h2 className="text-2xl font-semibold text-[#1A1A1A] mb-1">
                  {option.title}
                </h2>

                <p className="text-[#6B7280]">
                  {option.description}
                </p>
              </div>
            </div>

            <span className="text-2xl text-[#9CA3AF]">→</span>
          </button>
        ))}
      </div>

      <div className="text-center mt-12">
        <button className="px-6 py-3 rounded-full border border-[#D1D5DB] text-[#6B7280] hover:bg-gray-100 transition">
          Not ready to talk about it yet
        </button>

        <p className="text-sm text-[#9CA3AF] mt-3">
          Maya will check in again tomorrow.
        </p>
      </div>
    </div>
  );
}