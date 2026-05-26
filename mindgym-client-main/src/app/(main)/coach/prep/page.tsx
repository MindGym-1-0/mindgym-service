// src/app/(main)/coach/prep/page.tsx

"use client";

export default function CoachPrepPage() {
  const worries = [
    "Panel anxiety — multiple interviewers at once",
    "On-site pressure vs video",
    "Imposter syndrome at this seniority",
    "Portfolio review under scrutiny",
    "Blank mind on follow-up questions",
  ];

  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <div className="flex items-center gap-4 mb-8">
        <button className="w-10 h-10 rounded-full bg-white shadow">
          ←
        </button>

        <div>
          <h1 className="text-3xl font-semibold">
            Start prep — UX Lead @ Meta
          </h1>
          <p className="text-gray-500">
            Thu 2:00 PM • On-site Panel • 8 days away
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl p-5 shadow-sm mb-8">
        <p className="text-gray-700">
          “8 days is a solid runway. Let’s build your prep properly.”
        </p>

        <div className="mt-4 inline-block bg-[#DFF5EF] text-[#0D7C66] px-4 py-2 rounded-full text-sm">
          This creates a personalized prep plan for Meta
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Worries */}
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="font-semibold mb-4">
            What worries you the most?
          </h2>

          <div className="space-y-3">
            {worries.map((item, index) => (
              <div
                key={index}
                className={`border rounded-xl p-4 cursor-pointer ${
                  index === 0
                    ? "border-[#0D7C66] bg-[#E8F7F2]"
                    : "border-gray-200"
                }`}
              >
                {item}
              </div>
            ))}
          </div>
        </div>

        {/* Plan */}
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="font-semibold mb-4">
            Maya’s 8 day prep plan
          </h2>

          <div className="space-y-4">
            {[
              "Today — anxiety intake",
              "Day 2-3 — panel room visualization",
              "Day 4-5 — seniority confidence anchor",
              "Day 6-7 — portfolio walkthrough",
              "Morning of — 10 min calm reset",
            ].map((step, i) => (
              <div
                key={i}
                className="flex items-center gap-4"
              >
                <div className="w-8 h-8 rounded-full bg-[#0D7C66] text-white flex items-center justify-center text-sm">
                  {i + 1}
                </div>

                <p>{step}</p>
              </div>
            ))}
          </div>

          <button className="mt-8 bg-[#0D7C66] text-white px-6 py-3 rounded-xl">
            Start
          </button>
        </div>
      </div>
    </div>
  );
}