import type { Metadata } from "next";
import { PageMasthead } from "@/components/page-shell/PageMasthead";
import { ReportsClient } from "@/components/reports/ReportsClient";
import { STRINGS } from "@/lib/strings";

export const metadata: Metadata = { title: STRINGS.reports.title };

export default function ReportsPage() {
  return (
    <>
      <PageMasthead eyebrow={STRINGS.brand.ministry} title={STRINGS.reports.title} lede={STRINGS.reports.lede} />
      <ReportsClient />
    </>
  );
}
