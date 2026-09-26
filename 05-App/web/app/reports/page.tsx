import type { Metadata } from "next";
import { PageMasthead } from "@/components/page-shell/PageMasthead";
import { ReportsClient } from "@/components/reports/ReportsClient";
import { Str } from "@/components/shell/Str";
import { STRINGS } from "@/lib/strings";

export const metadata: Metadata = { title: STRINGS.reports.title };

export default function ReportsPage() {
  return (
    <>
      <PageMasthead
        eyebrow={<Str k="brand.ministry" />}
        title={<Str k="reports.title" />}
        lede={<Str k="reports.lede" />}
      />
      <ReportsClient />
    </>
  );
}
