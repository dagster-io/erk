import React from "react";
import { DocsThemeConfig } from "nextra-theme-docs";
import { useTheme } from "next-themes";

const Logo = () => {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <img
        src="/images/compass-logo.svg"
        alt="Dagster Compass"
        height={24}
        width={160}
      />
    );
  }

  return (
    <img
      src={
        resolvedTheme === "dark"
          ? "/images/compass-logo-dark.svg"
          : "/images/compass-logo.svg"
      }
      alt="Dagster Compass"
      height={24}
      width={160}
    />
  );
};

const config: DocsThemeConfig = {
  logo: <Logo />,
  project: {
    icon: null,
  },
  nextThemes: {
    defaultTheme: "system",
    storageKey: "theme",
  },
  sidebar: {
    defaultMenuCollapseLevel: 1,
    toggleButton: true,
  },
  themeSwitch: {
    useOptions() {
      return {
        light: "Light",
        dark: "Dark",
        system: "System",
      };
    },
  },
  useNextSeoProps() {
    return {
      titleTemplate: "%s – Compass Documentation",
      openGraph: {
        images: [
          {
            url: "/images/og-image.png",
            width: 1200,
            height: 630,
            alt: "Dagster Compass Documentation",
          },
        ],
      },
    };
  },
  head: (
    <>
      <meta property="og:image" content="/images/og-image.png" />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:image" content="/images/og-image.png" />
    </>
  ),
  editLink: {
    component: null,
  },
  feedback: {
    content: "Need help? Email us →",
    useLink: () => "mailto:compass-support@dagsterlabs.com",
  },
  footer: {
    component: (
      <footer
        style={{
          borderTop: "1px solid var(--nextra-border-color, #e5e7eb)",
          marginTop: 0,
          paddingTop: "3rem",
          paddingBottom: "3rem",
          backgroundColor: "var(--nextra-bg)",
          borderColor: "var(--nextra-border-color)",
        }}
      >
        <div
          style={{
            maxWidth: "90rem",
            margin: "0 auto",
            padding: "0 2rem",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "3rem",
              alignItems: "end",
            }}
          >
            {/* Left Column - Logo and Social */}
            <div>
              <div style={{ marginBottom: "1.5rem" }}>
                <Logo />
              </div>
              <p
                style={{
                  color: "var(--nextra-fg)",
                  marginBottom: "2rem",
                  opacity: 0.8,
                  fontSize: "16px",
                }}
              >
                Brought to you by{" "}
                <a
                  href="https://dagster.io"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    color: "var(--nextra-fg)",
                    fontWeight: "500",
                    textDecoration: "none",
                  }}
                >
                  Dagster Labs
                </a>
              </p>

              {/* Social Icons */}
              <div
                style={{
                  display: "flex",
                  gap: "1rem",
                }}
              >
                <a
                  href="https://github.com/dagster-io"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--nextra-fg)", opacity: 0.7 }}
                >
                  <svg
                    style={{ width: "20px", height: "20px" }}
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M12 0C5.374 0 0 5.373 0 12 0 17.302 3.438 21.8 8.207 23.387c.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
                  </svg>
                </a>
                <a
                  href="https://twitter.com/dagsterio"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--nextra-fg)", opacity: 0.7 }}
                >
                  <svg
                    style={{ width: "20px", height: "20px" }}
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                  </svg>
                </a>
                <a
                  href="https://www.linkedin.com/company/elementl"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--nextra-fg)", opacity: 0.7 }}
                >
                  <svg
                    style={{ width: "20px", height: "20px" }}
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                </a>
                <a
                  href="https://www.youtube.com/channel/UCfLnv9X8jyHTe6gJ4hVBo9Q"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--nextra-fg)", opacity: 0.7 }}
                >
                  <svg
                    style={{ width: "20px", height: "20px" }}
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                  </svg>
                </a>
              </div>
            </div>

            {/* Right Column - Legal and Copyright */}
            <div style={{ textAlign: "right" }}>
              <p
                style={{
                  fontSize: "14px",
                  color: "var(--nextra-fg)",
                  opacity: 0.7,
                  marginBottom: "1rem",
                }}
              >
                Copyright © 2025 Elementl, Inc. d.b.a. Dagster Labs. All rights
                reserved.
              </p>
              <div
                style={{
                  display: "flex",
                  gap: "1.5rem",
                  justifyContent: "flex-end",
                }}
              >
                <a
                  href="https://compass.dagster.io/terms"
                  target="_blank"
                  style={{
                    fontSize: "14px",
                    color: "var(--nextra-fg)",
                    opacity: 0.7,
                    textDecoration: "none",
                  }}
                >
                  Terms of Service
                </a>
                <a
                  href="https://dagster.io/privacy"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: "14px",
                    color: "var(--nextra-fg)",
                    opacity: 0.7,
                    textDecoration: "none",
                  }}
                >
                  Privacy Policy
                </a>
              </div>
            </div>
          </div>
        </div>
      </footer>
    ),
  },
};

export default config;
