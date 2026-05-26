// src/app/(main)/coach/interview-checkin/got-job/page.tsx

export default function GotJobPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="bg-[#005F56] rounded-3xl text-white p-10 text-center">
        <div className="text-6xl mb-6">🏆</div>

        <p className="text-sm mb-2 opacity-80">
          Product Designer @ Google
        </p>

        <h1 className="text-5xl font-bold mb-5">
          You got the job.
        </h1>

        <p className="max-w-2xl mx-auto text-lg opacity-90 leading-relaxed">
          6 prep sessions. 7-day streak. A confidence lift from
          4 to 8. You showed up for yourself every single day
          leading into this.
        </p>

        <div className="flex justify-center gap-4 mt-8">
          <button className="bg-white text-[#005F56] px-6 py-3 rounded-xl font-medium">
            Log offer
          </button>

          <button className="border border-white px-6 py-3 rounded-xl">
            Just take it in →
          </button>
        </div>
      </div>

      <div className="bg-white rounded-3xl p-8 shadow-sm">
        <h2 className="text-2xl font-bold mb-6">
          What comes next
        </h2>

        <div className="space-y-4">
          {[
            "Read the role compensation, start date, and negotiation window carefully.",
            "Most people leave money on the table because they skip negotiation prep.",
            "Starting a new role is its own kind of stressful.",
          ].map((item, index) => (
            <div
              key={index}
              className="border rounded-2xl p-5 flex justify-between items-center"
            >
              <p className="text-[#374151]">{item}</p>

              <button className="bg-[#005F56] text-white px-5 py-2 rounded-xl">
                Start
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-[#003B36] text-white rounded-3xl p-8">
        <p className="italic text-lg">
          “The job said yes because you were genuinely prepared.”
        </p>
      </div>
    </div>
  );
}