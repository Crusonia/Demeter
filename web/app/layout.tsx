import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Demeter · Learn by changing the system",
  description:
    "Explore food and health model assumptions, follow their effects, and test your reasoning.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
