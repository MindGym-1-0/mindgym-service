import { MessageCircleQuestion } from "lucide-react";

export default function SupportBanner() {
  return (
    <div className="mt-8 flex items-center justify-between rounded-3xl border border-[#E7E7E4] bg-white px-8 py-7 shadow-sm">
      <div className="flex items-start gap-5">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#E7F5F0]">
          <MessageCircleQuestion
            size={26}
            className="text-[#0C6B58]"
          />
        </div>

        <div>
          <h2 className="text-[42px] font-semibold leading-none text-[#0C6B58]">
            Still need help?
          </h2>

          <p className="mt-3 max-w-[700px] text-[15px] leading-7 text-[#5E5E5E]">
            We&apos;re a small team and we actually read every message.
            Response time is usually under 24 hours on weekdays.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="rounded-xl bg-[#0C6B58] px-6 py-3 text-sm font-medium text-white transition hover:opacity-90">
          Email support
        </button>

        <button className="rounded-xl border border-[#DADADA] bg-white px-6 py-3 text-sm font-medium text-[#1A1A1A] transition hover:bg-gray-50">
          Ask Maya
        </button>
      </div>
    </div>
  );
}