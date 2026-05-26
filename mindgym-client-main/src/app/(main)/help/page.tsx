import FAQCard from "../../../components/help/FAQCard";
import SupportBanner from "../../../components/help/SupportBanner";
import { faqItems } from "../../../lib/help-data";

export default function HelpPage() {
  return (
    <div className="mx-auto max-w-[1400px]">
      <div className="mb-10">
        <h1 className="text-[52px] font-semibold leading-none text-[#1A1A1A]">
          Help & FAQ
        </h1>

        <p className="mt-4 text-[18px] text-[#7A7A7A]">
          Everything you need to get the most from MindGym.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {faqItems.map((faq) => (
          <FAQCard
            key={faq.question}
            question={faq.question}
            answer={faq.answer}
          />
        ))}
      </div>

      <SupportBanner />
    </div>
  );
}