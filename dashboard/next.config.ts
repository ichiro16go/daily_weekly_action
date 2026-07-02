import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      // Legacy NextAuth paths from a previous auth attempt. Any residual
      // browser history / bookmarks pointing at these should land safely
      // on the home page instead of hitting a 404 (which then breaks the
      // post-login redirect flow).
      {
        source: "/api/auth/:path*",
        destination: "/",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
