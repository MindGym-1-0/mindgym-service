// src/app/(main)/progress/insights/page.tsx

"use client";

export default function InsightsPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] px-10 py-8">
      
      {/* Header */}
      <div>
        <p className="text-sm text-gray-500">
          Overview • Daily Dashboard
        </p>

        <h1 className="mt-4 text-4xl font-semibold">
          Insights
        </h1>

        <p className="mt-2 text-sm text-gray-500">
          Remember, progress is rarely a straight
          line — every step counts on your journey.
        </p>
      </div>

      {/* Top Insight Cards */}
      <div className="mt-8 grid grid-cols-1 gap-5 xl:grid-cols-2">
        
        <div className="rounded-3xl border border-[#0C6B58] bg-[#EAF8F4] p-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-[#0C6B58]">
            TOP INSIGHTS THIS WEEK
          </p>

          <h2 className="mt-4 text-lg font-semibold text-[#0C6B58]">
            You feel most grounded after breathing
            sessions
          </h2>

          <p className="mt-3 text-sm text-[#0C6B58]">
            Sessions with Phase 1 complete average
            +4.2 lift. Without: avg +1.8 lift.
          </p>
        </div>

        <div className="rounded-3xl border border-orange-300 bg-orange-50 p-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-orange-500">
            TOP INSIGHTS THIS WEEK
          </p>

          <h2 className="mt-4 text-lg font-semibold text-orange-600">
            Morning sessions produce stronger
            confidence lifts
          </h2>

          <p className="mt-3 text-sm text-orange-500">
            +2.1 higher avg lift before 10 AM vs
            evening sessions
          </p>
        </div>
      </div>

      {/* Mini Cards */}
      <div className="mt-6 grid grid-cols-1 gap-5 xl:grid-cols-3">
        
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="mb-4 h-3 w-3 rounded-full bg-[#0C6B58]" />

          <p className="text-sm text-gray-700">
            Interview anxiety is your most frequent
            emotional starting point
          </p>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="mb-4 h-3 w-3 rounded-full bg-orange-500" />

          <p className="text-sm text-gray-700">
            Rejection recovery sessions show the
            highest average lift (+5)
          </p>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="mb-4 h-3 w-3 rounded-full bg-red-400" />

          <p className="text-sm text-gray-700">
            Calmness is improving — up 8 points over
            the last 2 weeks
          </p>
        </div>
      </div>

      {/* Bottom Recommendation */}
      <div className="mt-8 rounded-3xl border border-blue-300 bg-blue-50 p-8">
        
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
          HIRING FUNNEL GAP IDENTIFIED
        </p>

        <h2 className="mt-4 text-xl font-semibold text-blue-700">
          You&apos;re getting recruiter calls but
          progress slows at the interview stage.
        </h2>

        <p className="mt-4 text-sm leading-7 text-blue-600">
          This is typically a confidence and
          composure challenge, not a skills gap.
          Focus:
        </p>

        <p className="mt-4 text-sm text-blue-600">
          Mental readiness before interviews
        </p>

        <p className="mt-6 text-sm text-blue-500">
          Based on 6 sessions • Confidence 72%,
          Structure 55%
        </p>
      </div>
    </div>
  );
}