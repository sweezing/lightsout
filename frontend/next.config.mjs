/** @type {import('next').NextConfig} */
const nextConfig = {
  // Small self-contained server for the Docker image.
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  // The API, WebSocket and media are served from the same origin by nginx,
  // so the browser never needs to know the backend's address.
};

export default nextConfig;
