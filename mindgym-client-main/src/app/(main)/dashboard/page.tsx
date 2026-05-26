// src/app/(dashboard)/page.tsx

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-5xl font-semibold text-[#1A1A1A]">
          Good morning, Claire. 👋
        </h1>

        <p className="mt-2 text-gray-500">
          Wednesday · 14 May · 8:43 AM
        </p>
      </div>

      <div className="rounded-3xl bg-[#0C6B58] p-8 text-white">
        <p className="mb-2 text-sm opacity-80">
          Final interview • Tomorrow • 10:00AM
        </p>

        <h2 className="max-w-md text-4xl font-semibold leading-tight">
          Product Designer @ Google
        </h2>

        <p className="mt-3 text-sm opacity-80">
          Google Meet • Final round • 6 prep sessions done
        </p>

        <div className="mt-6 flex gap-4">
          <button className="rounded-xl bg-white px-5 py-3 text-sm font-medium text-black">
            Prepare with Maya →
          </button>

          <button className="rounded-xl border border-white/30 px-5 py-3 text-sm">
            View details
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h3 className="text-4xl font-semibold text-[#0C6B58]">
            6
          </h3>

          <p className="mt-2 text-sm text-gray-500">
            Sessions done
          </p>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h3 className="text-4xl font-semibold text-[#F59E0B]">
            3🔥
          </h3>

          <p className="mt-2 text-sm text-gray-500">
            Day streak
          </p>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h3 className="text-4xl font-semibold text-[#0C6B58]">
            +12%
          </h3>

          <p className="mt-2 text-sm text-gray-500">
            Confidence lift
          </p>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h3 className="text-4xl font-semibold text-[#1A1A1A]">
            2
          </h3>

          <p className="mt-2 text-sm text-gray-500">
            Interviews set
          </p>
        </div>
      </div>
    </div>
  );
}