import type { Metadata } from "next";
import { DashboardHero } from "@/components/dashboard/DashboardHero";
import { DashboardClient } from "@/components/dashboard/DashboardClient";
import { STRINGS } from "@/lib/strings";

export const metadata: Metadata = { title: STRINGS.nav.dashboard };

export default function DashboardPage() {
  return (
    <>
      <DashboardHero />
      <DashboardClient />
    </>
  );
}
