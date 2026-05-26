// src/app/(main)/resources/page.tsx

"use client";

import Link from "next/link";

const resources = [
  {
    title: "Box breathing",
    description: "Calm nerves in 5 minutes",
    tag: "Mental reset",
    emoji: "🫁",
    href: "/resources/box-breathing",
    color: "bg-blue-50 text-blue-600",
  },

  {
    title: "Rejection recovery",
    description: "Reframe and move forward",
    tag: "Resilience",
    emoji: "💔",
    href: "#",
    color: "bg-red-50 text-red-500",
  },

  {
    title: "Managing anxiety",
    description: "Cognitive reframing techniques",
    tag: "Mental health",
    emoji: "🧠",
    href: "#",
    color: "bg-orange-50 text-orange-500",
  },

  {
    title: "Negotiating your offer",
    description: "Scripts for salary conversations",
    tag: "Guide",
    emoji: "💰",
    href: "#",
    color: "bg-green-50 text-green-600",
  },

  {
    title: "Confidence reset",
    description: "Calm yourself under pressure",
    tag: "Mental reset",
    emoji: "🎯",
    href: "#",
    color: "bg-indigo-50 text-indigo-500",
  },

  {
    title: "100 design interview questions",
    description: "Practice bank with sample answers",
    tag: "Practice",
    emoji: "❓",
    href: "#",
    color: "bg-yellow-50 text-yellow-600",
  },
];

export default function ResourcesPage() {
  return (
    <div className="min-h-screen bg-[#F6F6F4] px-10 py-8">
      
      {/* Header */}
      <div>
        <p className="text-sm text-gray-500">
          Learn • Resources
        </p>

        <h1 className="mt-4 text-4xl font-semibold">
          Resources
        </h1>

        <p className="mt-2 text-sm text-gray-500">
          Frameworks, guides, and mental tools
          to sharpen your preparation
        </p>
      </div>

      {/* Cards */}
      <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        
        {resources.map((resource) => (
          <Link
            key={resource.title}
            href={resource.href}
            className="rounded-3xl bg-white p-8 shadow-sm transition-all hover:-translate-y-1 hover:shadow-md"
          >
            <div className="text-4xl">
              {resource.emoji}
            </div>

            <h2 className="mt-6 text-xl font-semibold">
              {resource.title}
            </h2>

            <p className="mt-2 text-sm text-gray-500">
              {resource.description}
            </p>

            <div
              className={`mt-5 inline-flex rounded-full px-3 py-1 text-xs font-medium ${resource.color}`}
            >
              {resource.tag}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}