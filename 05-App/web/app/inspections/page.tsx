import type { Metadata } from "next";
import { Suspense } from "react";
import { PageMasthead } from "@/components/page-shell/PageMasthead";
import { InspectionListClient } from "@/components/inspection-list/InspectionListClient";
import { STRINGS } from "@/lib/strings";

export const metadata: Metadata = { title: STRINGS.nav.inspection_list };

export default function InspectionsPage() {
  return (
    <>
      <PageMasthead
        eyebrow={STRINGS.brand.ministry}
        title={STRINGS.nav.inspection_list}
        lede={STRINGS.framing.premise}
      />
      {/* The list reads its filters from the address bar (useSearchParams). */}
      <Suspense fallback={null}>
        <InspectionListClient />
      </Suspense>
    </>
  );
}
