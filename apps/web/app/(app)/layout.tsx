import { Shell } from "@/components/shell";
import type { ReactNode } from "react";

export default function AppLayout({ children }: { children: ReactNode }) {
  return <Shell>{children}</Shell>;
}
