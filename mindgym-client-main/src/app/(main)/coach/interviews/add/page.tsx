// src/app/(main)/coach/interviews/add/page.tsx

"use client";

import { useRouter } from "next/navigation";

export default function AddInterviewPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[#F6F6F4] p-8">
      
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        
        <button
          onClick={() => router.back()}
          className="w-10 h-10 rounded-full bg-white shadow flex items-center justify-center hover:bg-gray-100 transition"
        >
          ←
        </button>

        <h1 className="text-3xl font-semibold">
          Add interview
        </h1>
      </div>

      {/* Upload Section */}
      <div className="max-w-2xl mx-auto">
        
        <div className="bg-white border-2 border-dashed border-gray-300 rounded-2xl p-16 text-center shadow-sm">
          
          <div className="text-5xl mb-4">
            📤
          </div>

          <h2 className="text-lg font-semibold">
            Choose a file or drag and drop it here
          </h2>

          <p className="text-gray-500 mt-2">
            JPEG, PNG, PDF up to 30MB
          </p>

          <button className="mt-6 border border-gray-300 px-5 py-2 rounded-lg hover:bg-gray-100 transition">
            Browse file
          </button>
        </div>

        {/* Notes */}
        <div className="mt-8">
          
          <label className="text-sm text-gray-600 font-medium">
            Notes (Optional)
          </label>

          <textarea
            placeholder="Add any specific details or job description links here..."
            className="w-full mt-2 p-4 rounded-xl border border-gray-300 h-40 resize-none focus:outline-none focus:ring-2 focus:ring-[#0D7C66]"
          />
        </div>

        {/* Submit Button */}
        <div className="mt-8 flex justify-end">
          
          <button className="bg-[#0D7C66] text-white px-6 py-3 rounded-xl hover:bg-[#095c4c] transition">
            Save Interview
          </button>
        </div>
      </div>
    </div>
  );
}