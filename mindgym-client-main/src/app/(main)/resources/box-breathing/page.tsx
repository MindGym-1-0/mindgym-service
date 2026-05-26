// src/app/(main)/resources/box-breathing/page.tsx

"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

const steps = [
  {
    title: "Sit upright",
    description:
      "Find a comfortable position. Feet flat, shoulders relaxed.",
  },

  {
    title: "Inhale for 4 counts",
    description:
      "Breathe in deeply through your nose.",
  },

  {
    title: "Hold for 4 counts",
    description:
      "Keep the breath in. Don’t tense up.",
  },

  {
    title: "Exhale for 4 counts",
    description:
      "Release slowly through your mouth.",
  },

  {
    title: "Hold for 4 counts",
    description:
      "Empty lungs. Pause before the next cycle.",
  },

  {
    title: "Repeat 4 cycles",
    description:
      "One full box takes about 2 minutes.",
  },
];

export default function BoxBreathingPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] px-10 py-8">
      
      {/* Back */}
      <Link
        href="/resources"
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-black"
      >
        <ArrowLeft size={18} />
        Back to resources
      </Link>

      {/* Top Card */}
      <div className="mt-6 rounded-3xl border border-[#0C6B58] bg-[#DDF4EE] p-8">
        
        <div className="flex items-start justify-between">
          
          <div className="flex gap-5">
            
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white text-4xl">
              🫁
            </div>

            <div>
              <div className="inline-flex rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-600">
                Mental reset
              </div>

              <h1 className="mt-3 text-3xl font-semibold text-[#0C6B58]">
                Box breathing
              </h1>

              <p className="mt-2 text-sm text-[#0C6B58]">
                Calm nerves in 5 minutes,
                anywhere
              </p>
            </div>
          </div>

          <div className="text-right">
            <p className="text-xs text-gray-500">
              DURATION
            </p>

            <p className="mt-1 text-xl font-semibold">
              5 Minutes
            </p>

            <button className="mt-4 rounded-xl bg-[#0C6B58] px-5 py-2 text-white transition-all hover:opacity-90">
              Start now
            </button>
          </div>
        </div>
      </div>

      {/* Main Layout */}
      <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-3">
        
        {/* Left */}
        <div className="xl:col-span-2 space-y-6">
          
          {/* What this is */}
          <div className="rounded-3xl bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold">
              What this is
            </h2>

            <p className="mt-4 text-sm leading-7 text-gray-600">
              Box breathing is a scientifically
              backed breathing technique used to
              regulate the nervous system under
              pressure.
            </p>

            <p className="mt-4 text-sm leading-7 text-gray-600">
              It works by balancing oxygen and CO2
              levels, activating the parasympathetic
              response and reducing cortisol.
            </p>
          </div>

          {/* Steps */}
          <div className="rounded-3xl bg-white p-6 shadow-sm">
            
            <h2 className="text-lg font-semibold">
              How to do it
            </h2>

            <div className="mt-6 space-y-4">
              
              {steps.map((step, index) => (
                <div
                  key={step.title}
                  className="flex gap-4 rounded-2xl border border-gray-100 p-5"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#DDF4EE] text-sm font-semibold text-[#0C6B58]">
                    {index + 1}
                  </div>

                  <div>
                    <h3 className="font-medium">
                      {step.title}
                    </h3>

                    <p className="mt-1 text-sm text-gray-500">
                      {step.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right */}
        <div className="space-y-6">
          
          {/* Why it works */}
          <div className="rounded-3xl bg-white p-6 shadow-sm">
            
            <h2 className="text-lg font-semibold">
              Why it works
            </h2>

            <p className="mt-4 text-sm leading-7 text-gray-600">
              Controlled breathing directly
              stimulates the vagus nerve — helping
              your body shift from stress mode into
              recovery mode.
            </p>
          </div>

          {/* Related */}
          <div className="rounded-3xl bg-white p-6 shadow-sm">
            
            <h2 className="text-lg font-semibold">
              Related resources
            </h2>

            <div className="mt-5 space-y-4">
              
              <div className="flex items-center justify-between rounded-2xl border border-gray-100 p-4">
                <span>
                  💔 Rejection recovery
                </span>

                <span>→</span>
              </div>

              <div className="flex items-center justify-between rounded-2xl border border-gray-100 p-4">
                <span>
                  🧠 Managing anxiety
                </span>

                <span>→</span>
              </div>

              <div className="flex items-center justify-between rounded-2xl border border-gray-100 p-4">
                <span>
                  🎯 Confidence reset
                </span>

                <span>→</span>
              </div>
            </div>
          </div>

          {/* Maya Recommendation */}
          <div className="rounded-3xl bg-[#083B32] p-6 text-white">
            
            <p className="text-xs uppercase tracking-wide text-green-200">
              Maya recommends this when
            </p>

            <p className="mt-4 text-sm leading-7 text-green-50">
              You&apos;re overwhelmed, anxious
              before an interview, or need a quick
              emotional reset before a high-pressure
              situation.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}