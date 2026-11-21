/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  distDir: process.env.BIZBAZAAR_NEXT_DIST_DIR || '.next',
  transpilePackages: [],
};

export default nextConfig;
