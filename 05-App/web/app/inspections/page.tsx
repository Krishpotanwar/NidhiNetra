import type { Metadata } from "next";
import { Suspense } from "react";
import { PageMasthead } from "@/components/page-shell/PageMasthead";
import { InspectionListClient } from "@/components/inspection-list/InspectionListClient";
import { Str } from "@/components/shell/Str";
import { STRINGS } from "@/lib/strings";

export const metadata: Metadata = { title: STRINGS.nav.inspection_list };

export default function InspectionsPage() {
  return (
    <>
      <PageMasthead
        eyebrow={<Str k="brand.ministry" />}
        title={<Str k="nav.inspection_list" />}
        lede={<Str k="framing.premise" />}
      />
      {/* The list reads its filters from the address bar (useSearchParams). */}
      <Suspense fallback={null}>
        <InspectionListClient />
      </Suspense>
    </>
  );
}
