type FAQCardProps = {
  question: string;
  answer: string;
};

export default function FAQCard({
  question,
  answer,
}: FAQCardProps) {
  return (
    <div className="rounded-3xl border border-[#E7E7E4] bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-[20px] font-semibold leading-snug text-[#0C6B58]">
        {question}
      </h3>

      <p className="text-[15px] leading-7 text-[#5E5E5E]">
        {answer}
      </p>
    </div>
  );
}