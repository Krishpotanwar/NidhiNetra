import type { Metadata } from "next";
import { Suspense } from "react";
import { PageMasthead } from "@/components/page-shell/PageMasthead";
import { FundFlowClient } from "@/components/fund-flow/FundFlowClient";
import { STRINGS } from "@/lib/strings";

export const metadata: Metadata = { title: STRINGS.fund_flow.title };

export default function FundFlowPage() {
  return (
    <>
      <PageMasthead
        eyebrow={STRINGS.brand.ministry}
        title={STRINGS.fund_flow.title}
        lede={STRINGS.fund_flow.subtitle}
      />
      {/* Reads ?agency= / ?vendor= deep links from a flagged row. */}
      <Suspense fallback={null}>
        <FundFlowClient />
      </Suspense>
    </>
  );
}
