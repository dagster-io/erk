import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightThemeBlack from "starlight-theme-black";

export default defineConfig({
  integrations: [
    starlight({
      plugins: [starlightThemeBlack({})],
      title: "Erk",
      description: "Plan-oriented agentic engineering",
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/dagster-io/erk",
        },
      ],
      customCss: ["./src/styles/custom.css"],
      sidebar: [
        {
          label: "Code Reviews",
          autogenerate: { directory: "code-reviews" },
        },
      ],
    }),
  ],
});
