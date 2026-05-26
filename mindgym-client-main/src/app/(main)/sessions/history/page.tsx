// src/app/(main)/sessions/history/page.tsx

"use client";

const history = [
  {
    title: "Calm Reset",
    confidence: "+4 lift",
    emoji: "😌",
  },
  {
    title: "Rejection Recovery",
    confidence: "+4 lift",
    emoji: "💔",
  },
  {
    title: "Confidence Builder",
    confidence: "+4 lift",
    emoji: "💪",
  },
];

export default function SessionHistoryPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      <h1 className="text-4xl font-semibold mb-2">
        Session history
      </h1>

      <p className="text-gray-500 mb-8">
        Your coaching sessions over time.
      </p>

      <div className="space-y-4">
        {history.map((item) => (
          <div
            key={item.title}
            className="bg-white rounded-2xl border p-5 flex items-center justify-between"
          >
            <div className="flex items-center gap-4">
              <div className="text-3xl">
                {item.emoji}
              </div>

              <div>
                <h2 className="font-semibold">
                  {item.title}
                </h2>

                <p className="text-sm text-gray-500">
                  Confidence +4
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm">
                {item.confidence}
              </div>

              <button className="bg-[#0C6B58] text-white px-4 py-2 rounded-lg">
                Replay
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}