// src/app/(main)/coach/checklist/page.tsx

"use client";

export default function ChecklistPage() {
  const checklist = [
    "Completed 6 coaching sessions",
    "Breathing session done last night",
    "Final grounding session tonight",
    "Questions to ask prepared",
    "Quiet space confirmed",
  ];

  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <h1 className="text-3xl font-semibold mb-8">
        Interview Checklist
      </h1>

      <div className="bg-white rounded-2xl p-6 shadow-sm mb-8">
        <div className="flex items-center justify-between">
          <p className="font-medium">Overall readiness</p>

          <p className="text-[#0D7C66] font-semibold">
            8/10 Complete
          </p>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-3 mt-4">
          <div className="bg-[#0D7C66] h-3 rounded-full w-[80%]" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="font-semibold mb-4">
            Mental & Emotional Prep
          </h2>

          <div className="space-y-4">
            {checklist.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3"
              >
                <div className="w-6 h-6 rounded-full bg-[#0D7C66] text-white flex items-center justify-center text-sm">
                  ✓
                </div>

                <p>{item}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[#0D3B32] text-white rounded-2xl p-6">
          <h2 className="font-semibold mb-4">
            Remember
          </h2>

          <p className="text-lg leading-relaxed">
            “Nervousness and excitement are the same feeling.
            Tell yourself you’re excited — and mean it.”
          </p>
        </div>
      </div>
    </div>
  );
}