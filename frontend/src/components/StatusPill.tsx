import { BOOKING_LABEL, ENQUIRY_LABEL, PLAN_ITEM_LABEL, QUOTATION_LABEL } from "../lib/format";
import type { BookingStatus, EnquiryStatus, PlanItemStatus, QuotationStatus } from "../types";

type Tone = "amber" | "green" | "red" | "grey" | "blue" | "maroon";

const TONES: Record<Tone, string> = {
  amber: "bg-amber-100 text-amber-900",
  green: "bg-green-100 text-green-800",
  red: "bg-red-100 text-red-800",
  grey: "bg-stone-200 text-stone-700",
  blue: "bg-sky-100 text-sky-800",
  maroon: "bg-maroon-100 text-maroon-800",
};

function Pill({ tone, label }: { tone: Tone; label: string }) {
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>{label}</span>;
}

const enquiryTone: Record<EnquiryStatus, Tone> = { pending: "amber", quoted: "blue", declined: "red", cancelled: "grey", closed: "green" };
const quotationTone: Record<QuotationStatus, Tone> = { sent: "amber", accepted: "green", rejected: "grey", withdrawn: "grey", expired: "grey" };
const bookingTone: Record<BookingStatus, Tone> = { requested: "amber", confirmed: "green", completed: "blue", cancelled: "grey", rejected: "red" };
const planTone: Record<PlanItemStatus, Tone> = { planned: "grey", shortlisted: "amber", booked: "blue", paid: "green", cancelled: "grey" };

export const EnquiryPill = ({ status }: { status: EnquiryStatus }) => <Pill tone={enquiryTone[status]} label={ENQUIRY_LABEL[status]} />;
export const QuotationPill = ({ status }: { status: QuotationStatus }) => <Pill tone={quotationTone[status]} label={QUOTATION_LABEL[status]} />;
export const BookingPill = ({ status }: { status: BookingStatus }) => <Pill tone={bookingTone[status]} label={BOOKING_LABEL[status]} />;
export const PlanItemPill = ({ status }: { status: PlanItemStatus }) => <Pill tone={planTone[status]} label={PLAN_ITEM_LABEL[status]} />;
