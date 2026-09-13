import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // lib/strings.ts and lib/data.ts import contracts/ directly (the frozen
  // data and copy contract lives one level up, at "05 App/contracts/", not
  // inside web/). Turbopack only resolves files at or below its root, which
  // it otherwise infers from the nearest lockfile (web/package-lock.json),
  // so contracts/ needs to be named explicitly here.
  turbopack: {
    root: path.join(__dirname, ".."),
  },
};

export default nextConfig;
