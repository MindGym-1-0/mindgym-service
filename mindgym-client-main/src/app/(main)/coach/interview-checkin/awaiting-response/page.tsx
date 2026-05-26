// src/app/(main)/coach/interview-checkin/awaiting-response/page.tsx

export default function AwaitingResponsePage() {
  const followUps = [
    "In 3 days",
    "In 5 days",
    "In 1 week",
    "When I hear back",
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div className="bg-[#F6EAD2] rounded-3xl p-10 text-center">
        <div className="text-6xl mb-5">⏰</div>

        <p className="text-sm text-[#9C6B00] mb-3">
          Product Designer @ Google
        </p>

        <h1 className="text-5xl font-bold text-[#3F2E00] mb-5">
          You’ve done your part.
        </h1>

        <p className="text-[#6B5A2B] max-w-2xl mx-auto text-lg">
          The interview is over. Your preparation was real.
          Whatever they decide, you showed up as your best self.
        </p>

        <div className="flex justify-center gap-4 mt-8">
          <button className="bg-[#005F56] text-white px-6 py-3 rounded-xl">
            Set a follow-up reminder →
          </button>

          <button className="border border-[#D6C7A4] px-6 py-3 rounded-xl">
            Log how it felt
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-3xl p-6">
          <h2 className="text-xl font-bold mb-4">
            Practical
          </h2>

          <ul className="space-y-3 text-[#4B5563]">
            <li>• If you haven’t heard in 5 business days, a polite follow-up is normal.</li>
            <li>• Keep applying elsewhere.</li>
            <li>• Write Maya to draft a follow-up note.</li>
          </ul>
        </div>

        <div className="bg-white rounded-3xl p-6">
          <h2 className="text-xl font-bold mb-4">
            Emotional
          </h2>

          <ul className="space-y-3 text-[#4B5563]">
            <li>• Anxiety during the wait is normal.</li>
            <li>• The outcome doesn’t retroactively change your preparation.</li>
            <li>• A short grounding session can help.</li>
          </ul>
        </div>
      </div>

      <div className="bg-white rounded-3xl p-6">
        <h2 className="text-2xl font-bold mb-5">
          When should Maya check in with you?
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {followUps.map((item, index) => (
            <button
              key={index}
              className="border rounded-2xl py-4 hover:bg-[#E6F7F4] transition"
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-[#003B36] text-white rounded-3xl p-8">
        <p className="italic text-lg">
          “While you wait — keep moving forward.”
        </p>
      </div>
    </div>
  );
}